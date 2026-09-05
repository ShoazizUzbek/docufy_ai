"""Document intelligence: auto-classification + basic entity extraction.

Both come from a single LLM call over the document's text — one call
instead of two, since they're both cheap, best-effort reads of the same
content. Unlike extraction/chunking/embedding, a failure here doesn't fail
the whole document: classification and entities are supplementary
metadata, not required for the document to be searchable or askable.
"""

import json
import logging
import re

from ai_gateway import AIGatewayError, ai_chat
from ..models import Document

logger = logging.getLogger(__name__)

# Keeps the prompt (and cost) bounded for very large documents. Best-effort
# by nature — see CLAUDE.md Phase 6 deviations for why this isn't chunked
# and aggregated instead.
MAX_INPUT_CHARS = 12000

SYSTEM_INSTRUCTIONS = """You are a document analysis assistant. Given the text of a document, do two things:

1. Classify it into exactly one category: CONTRACT, REGULATION, POLICY, REPORT, or OTHER.
2. Extract key entities actually mentioned in the text: dates, monetary amounts, and party names (people or organizations named as parties, signatories, or subjects of the document).

Respond with a single JSON object and nothing else — no markdown code fences, no commentary — with exactly these keys:
- "category": one of "CONTRACT", "REGULATION", "POLICY", "REPORT", "OTHER"
- "dates": array of strings, dates as written in the text. Empty array if none.
- "amounts": array of strings, monetary amounts as written in the text. Empty array if none.
- "parties": array of strings, names of people or organizations. Empty array if none."""

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_EMPTY_ENTITIES = {'dates': [], 'amounts': [], 'parties': []}


def _build_document_text(document: Document) -> str:
    chunks = document.chunks.order_by('page_number', 'index')
    text = '\n\n'.join(c.text for c in chunks)
    return text[:MAX_INPUT_CHARS]


def _parse_response(raw_text: str) -> dict | None:
    cleaned = _JSON_FENCE_RE.sub('', raw_text.strip()).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    category = data.get('category')
    if category not in Document.Category.values:
        category = Document.Category.OTHER

    def _string_list(key):
        value = data.get(key, [])
        return [str(v) for v in value if isinstance(v, (str, int, float))] if isinstance(value, list) else []

    return {
        'category': category,
        'entities': {
            'dates': _string_list('dates'),
            'amounts': _string_list('amounts'),
            'parties': _string_list('parties'),
        },
    }


def analyze_document(document: Document) -> None:
    """Classifies the document and extracts basic entities, saving the
    result directly. Never raises — logs and leaves category/entities
    unset on any failure, since this is supplementary to the core
    pipeline, not required for it."""
    text = _build_document_text(document)
    if not text.strip():
        return

    messages = [
        {'role': 'system', 'content': SYSTEM_INSTRUCTIONS},
        {'role': 'user', 'content': text},
    ]

    try:
        raw_reply = ai_chat(messages, temperature=0.0, max_tokens=1024)
    except AIGatewayError:
        logger.warning('AI Gateway call failed while analyzing document %s', document.id)
        return

    parsed = _parse_response(raw_reply)
    if parsed is None:
        logger.warning('Could not parse document analysis response for %s: %r', document.id, raw_reply[:500])
        return

    document.category = parsed['category']
    document.entities = parsed['entities']
    document.save(update_fields=['category', 'entities', 'updated_at'])
