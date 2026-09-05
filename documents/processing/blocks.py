import re
from dataclasses import dataclass
from typing import Optional

# Keywords that commonly introduce a heading in the document types this
# platform targets (contracts, regulations, policies) across English,
# Russian, and Uzbek.
_HEADING_KEYWORDS = re.compile(
    r"^(chapter|part|section|article|"
    r"глава|раздел|статья|"
    r"bo['‘’]lim|modda|bob)\b",
    re.IGNORECASE,
)


@dataclass
class RawBlock:
    """A single extracted paragraph/line before hierarchy is resolved."""

    text: str
    page_number: Optional[int]
    is_heading: bool = False
    heading_level: int = 1


@dataclass
class EnrichedBlock:
    text: str
    page_number: Optional[int]
    is_heading: bool
    section_heading: str
    hierarchy_path: str


def detect_heading_by_text(text: str) -> tuple[bool, int]:
    """Best-effort heading detection from text alone (no font/style info) —
    used for plain text and OCR output. Returns (is_heading, level)."""
    stripped = text.strip()
    if not stripped or len(stripped) > 100:
        return False, 1

    if _HEADING_KEYWORDS.match(stripped):
        lowered = stripped.lower()
        if lowered.startswith(("chapter", "part", "глава", "bob")):
            return True, 1
        return True, 2

    letters = [c for c in stripped if c.isalpha()]
    if letters and stripped == stripped.upper() and len(letters) >= 3 and len(stripped) <= 80:
        return True, 1

    return False, 1


def assign_hierarchy(blocks: list[RawBlock]) -> list[EnrichedBlock]:
    """Walk blocks in document order, tracking a stack of open headings by
    level, to compute each block's nearest heading and full hierarchy path
    (e.g. "Chapter 2 > Article 14")."""
    stack: list[tuple[int, str]] = []
    enriched: list[EnrichedBlock] = []

    for block in blocks:
        if block.is_heading:
            heading_text = block.text.strip()
            while stack and stack[-1][0] >= block.heading_level:
                stack.pop()
            stack.append((block.heading_level, heading_text))

        hierarchy_path = " > ".join(text for _, text in stack)
        section_heading = stack[-1][1] if stack else ""

        enriched.append(
            EnrichedBlock(
                text=block.text,
                page_number=block.page_number,
                is_heading=block.is_heading,
                section_heading=section_heading,
                hierarchy_path=hierarchy_path,
            )
        )

    return enriched
