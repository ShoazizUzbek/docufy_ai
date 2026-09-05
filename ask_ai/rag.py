import json
import logging
import re

from django.conf import settings

from ai_gateway import AIGatewayError, ai_chat
from documents.processing.embeddings import embed_query
from documents.processing.vector_store import search as search_chunks

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTIONS = """You are Docufy AI, a document assistant. Answer the user's question using ONLY the numbered document excerpts provided as context. Do not use any outside knowledge, and do not guess.

Respond with a single JSON object and nothing else — no markdown code fences, no commentary before or after — with exactly these keys:
- "answer": (string) your answer in plain text, written for the person asking. If the excerpts don't contain enough information to answer confidently, briefly say so instead of guessing.
- "cited_sources": (array of integers) the excerpt numbers you actually relied on to write the answer. Empty array if you could not answer.
- "confident": (boolean) true only if the excerpts clearly support your answer.
- "follow_up_questions": (array of 0-3 short strings) natural follow-up questions the user might ask next, based on the excerpts. Empty array if none make sense."""

NO_DOCUMENTS_MESSAGE = (
    "I don't have any documents to search yet. Upload some documents first, then ask me again."
)
NO_DOCUMENT_CONTENT_MESSAGE = (
    "This document doesn't have any processed content yet — it may still be processing, or "
    "processing may have failed."
)
NO_MATCH_MESSAGE = (
    "I couldn't find anything in your documents that clearly answers this question."
)
UNAVAILABLE_MESSAGE = (
    "I couldn't reach the AI service to answer that just now. Please try again shortly."
)

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _empty_result(answer: str, sources: list[dict] | None = None) -> dict:
    return {
        'answer': answer,
        'confident': False,
        'citations': [],
        'sources': sources or [],
        'follow_up_questions': [],
    }


def _format_source(point, index: int) -> dict:
    payload = point.payload or {}
    return {
        'index': index,
        'chunk_id': str(point.id),
        'document_id': payload.get('document_id', ''),
        'original_filename': payload.get('original_filename', ''),
        'page_number': payload.get('page_number'),
        'section_heading': payload.get('section_heading', ''),
        'hierarchy_path': payload.get('hierarchy_path', ''),
        'text': payload.get('text', ''),
        'score': point.score,
    }


def _build_context_block(sources: list[dict]) -> str:
    parts = []
    for source in sources:
        location_bits = [source['original_filename']]
        if source['page_number']:
            location_bits.append(f"page {source['page_number']}")
        if source['hierarchy_path']:
            location_bits.append(source['hierarchy_path'])
        header = f"Excerpt [{source['index']}] ({', '.join(location_bits)}):"
        parts.append(f"{header}\n{source['text']}")
    return '\n\n'.join(parts)


def _build_messages(conversation_history: list[dict], question: str) -> list[dict]:
    messages = [{'role': 'system', 'content': SYSTEM_INSTRUCTIONS}]
    for turn in conversation_history:
        messages.append({'role': 'user', 'content': turn['question']})
        messages.append({'role': 'assistant', 'content': turn['answer']})
    messages.append({'role': 'user', 'content': question})
    return messages


def _parse_llm_response(raw_text: str) -> dict | None:
    cleaned = _JSON_FENCE_RE.sub('', raw_text.strip()).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict) or 'answer' not in data:
        return None

    return {
        'answer': str(data.get('answer', '')),
        'confident': bool(data.get('confident', False)),
        'cited_sources': [i for i in data.get('cited_sources', []) if isinstance(i, int)],
        'follow_up_questions': [q for q in data.get('follow_up_questions', []) if isinstance(q, str)][:3],
    }


def answer_question(
    question: str,
    organization_id,
    conversation_history: list[dict] | None = None,
    document_id=None,
) -> dict:
    """Retrieves relevant chunks and asks the LLM to answer strictly from
    them, citing which it used. Returns a low-confidence result (never
    raises) if there's nothing to search, nothing relevant enough, the
    model's response can't be parsed, or the LLM backend is unavailable.

    `document_id` scopes retrieval to one document — the Document Viewer's
    "Ask about this document" — instead of the whole organization.
    """
    conversation_history = conversation_history or []

    query_vector = embed_query(question)
    points = search_chunks(query_vector, organization_id, limit=settings.RAG_TOP_K, document_id=document_id)

    if not points:
        return _empty_result(NO_DOCUMENT_CONTENT_MESSAGE if document_id else NO_DOCUMENTS_MESSAGE)

    if points[0].score < settings.RAG_MIN_SCORE:
        weak_sources = [_format_source(p, i) for i, p in enumerate(points, start=1)]
        return _empty_result(NO_MATCH_MESSAGE, sources=weak_sources)

    sources = [_format_source(p, i) for i, p in enumerate(points, start=1)]
    context = _build_context_block(sources)
    messages = _build_messages(conversation_history, question)

    try:
        raw_reply = ai_chat(messages, context=context, temperature=0.0, max_tokens=1024)
    except AIGatewayError:
        logger.exception('AI Gateway call failed while answering a question')
        return _empty_result(UNAVAILABLE_MESSAGE, sources=sources)

    parsed = _parse_llm_response(raw_reply)
    if parsed is None:
        logger.warning('Could not parse LLM response as JSON: %r', raw_reply[:500])
        return {
            'answer': raw_reply.strip(),
            'confident': False,
            'citations': [],
            'sources': sources,
            'follow_up_questions': [],
        }

    cited_indices = set(parsed['cited_sources'])
    citations = [s for s in sources if s['index'] in cited_indices]

    return {
        'answer': parsed['answer'],
        'confident': parsed['confident'] and bool(citations),
        'citations': citations,
        'sources': sources,
        'follow_up_questions': parsed['follow_up_questions'],
    }
