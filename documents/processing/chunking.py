import re

from .blocks import EnrichedBlock
from .tokens import estimate_tokens

DEFAULT_MIN_TOKENS = 200
DEFAULT_MAX_TOKENS = 500

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_oversized_text(text: str, max_tokens: int) -> list[str]:
    """Split a single paragraph that alone exceeds max_tokens, first by
    sentence, falling back to a hard word-count split for any sentence
    that is itself still too long."""
    sentences = _SENTENCE_SPLIT_RE.split(text) or [text]
    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0

    def flush():
        if current:
            pieces.append(" ".join(current))
            current.clear()

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if sentence_tokens > max_tokens:
            flush()
            current_tokens = 0
            words = sentence.split()
            for i in range(0, len(words), max_tokens):
                pieces.append(" ".join(words[i : i + max_tokens]))
            continue

        if current and current_tokens + sentence_tokens > max_tokens:
            flush()
            current_tokens = 0

        current.append(sentence)
        current_tokens += sentence_tokens

    flush()
    return pieces


def chunk_blocks(
    blocks: list[EnrichedBlock],
    min_tokens: int = DEFAULT_MIN_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[dict]:
    """Group enriched blocks into paragraph/section-level chunks targeting
    min_tokens-max_tokens, never merging across a hierarchy (section)
    boundary. Returns a list of dicts ready to become Chunk rows, with a
    sequential "index" assigned."""
    chunks: list[dict] = []
    current_texts: list[str] = []
    current_tokens = 0
    current_page = None
    current_section = ""
    current_path = ""

    def flush():
        nonlocal current_texts, current_tokens
        if current_texts:
            chunks.append(
                {
                    "text": "\n\n".join(current_texts).strip(),
                    "page_number": current_page,
                    "section_heading": current_section,
                    "hierarchy_path": current_path,
                    "token_count": current_tokens,
                }
            )
        current_texts = []
        current_tokens = 0

    for block in blocks:
        text = block.text.strip()
        if not text:
            continue

        tokens = estimate_tokens(text)
        starts_new_section = bool(current_texts) and block.hierarchy_path != current_path
        would_overflow = current_tokens + tokens > max_tokens and current_tokens >= min_tokens

        if starts_new_section or would_overflow:
            flush()

        if not current_texts:
            current_page = block.page_number
            current_section = block.section_heading
            current_path = block.hierarchy_path

        if tokens > max_tokens:
            flush()
            for piece in _split_oversized_text(text, max_tokens):
                chunks.append(
                    {
                        "text": piece,
                        "page_number": block.page_number,
                        "section_heading": block.section_heading,
                        "hierarchy_path": block.hierarchy_path,
                        "token_count": estimate_tokens(piece),
                    }
                )
            continue

        current_texts.append(text)
        current_tokens += tokens

    flush()

    for i, chunk in enumerate(chunks):
        chunk["index"] = i

    return chunks
