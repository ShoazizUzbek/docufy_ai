import re
import statistics
from io import BytesIO

import pymupdf
from docx import Document as DocxDocument
from docx.oxml.ns import qn

from .blocks import RawBlock, detect_heading_by_text
from .ocr import run_ocr

# Below this average of extracted characters per page, a PDF is treated as
# scanned (no usable text layer) and routed through OCR instead.
TEXT_LAYER_MIN_CHARS_PER_PAGE = 20


def extract_pdf(file_bytes: bytes) -> tuple[list[RawBlock], int, bool]:
    """Returns (blocks, page_count, used_ocr)."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    try:
        page_count = doc.page_count
        pages_lines: list[list[tuple[str, float]]] = []
        total_chars = 0

        for page in doc:
            page_dict = page.get_text("dict")
            lines: list[tuple[str, float]] = []
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:  # not a text block
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(span.get("text", "") for span in spans).strip()
                    if not text:
                        continue
                    size = max((span.get("size", 0) for span in spans), default=0)
                    lines.append((text, size))
                    total_chars += len(text)
            pages_lines.append(lines)

        avg_chars_per_page = total_chars / max(page_count, 1)
        if avg_chars_per_page < TEXT_LAYER_MIN_CHARS_PER_PAGE:
            blocks = _extract_pdf_via_ocr(doc)
            return blocks, page_count, True

        sizes = [round(size) for lines in pages_lines for _, size in lines]
        try:
            body_size = statistics.mode(sizes) if sizes else 10
        except statistics.StatisticsError:
            body_size = statistics.median(sizes) if sizes else 10

        blocks: list[RawBlock] = []
        for page_index, lines in enumerate(pages_lines, start=1):
            for text, size in lines:
                is_heading = size > body_size * 1.15 and len(text) < 120
                level = 1 if size > body_size * 1.4 else 2
                blocks.append(
                    RawBlock(text=text, page_number=page_index, is_heading=is_heading, heading_level=level)
                )

        return blocks, page_count, False
    finally:
        doc.close()


def _extract_pdf_via_ocr(doc: "pymupdf.Document") -> list[RawBlock]:
    blocks: list[RawBlock] = []
    for page_index in range(doc.page_count):
        page = doc[page_index]
        pixmap = page.get_pixmap(dpi=200)
        image_bytes = pixmap.tobytes("png")
        for line_text in run_ocr(image_bytes):
            is_heading, level = detect_heading_by_text(line_text)
            blocks.append(
                RawBlock(text=line_text, page_number=page_index + 1, is_heading=is_heading, heading_level=level)
            )
    return blocks


_HEADING_STYLE_RE = re.compile(r"heading\s*(\d+)", re.IGNORECASE)


def extract_docx(file_bytes: bytes) -> tuple[list[RawBlock], int]:
    doc = DocxDocument(BytesIO(file_bytes))
    blocks: list[RawBlock] = []
    page_number = 1

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style else ""
        heading_match = _HEADING_STYLE_RE.match(style_name or "")
        is_heading = bool(heading_match) or style_name == "Title"
        level = int(heading_match.group(1)) if heading_match else 1

        if text:
            blocks.append(RawBlock(text=text, page_number=page_number, is_heading=is_heading, heading_level=level))

        has_page_break = any(
            br.get(qn("w:type")) == "page"
            for run in paragraph.runs
            for br in run._element.findall(qn("w:br"))
        )
        if has_page_break:
            page_number += 1

    return blocks, page_number


def extract_txt(file_bytes: bytes) -> tuple[list[RawBlock], int]:
    content = file_bytes.decode("utf-8", errors="replace")

    pages = content.split("\x0c") if "\x0c" in content else [content]
    blocks: list[RawBlock] = []

    for page_index, page_text in enumerate(pages, start=1):
        for paragraph in re.split(r"\n\s*\n", page_text):
            text = paragraph.strip()
            if not text:
                continue
            is_heading, level = detect_heading_by_text(text)
            blocks.append(RawBlock(text=text, page_number=page_index, is_heading=is_heading, heading_level=level))

    return blocks, len(pages)


def extract_image(file_bytes: bytes) -> tuple[list[RawBlock], int]:
    blocks: list[RawBlock] = []
    for line_text in run_ocr(file_bytes):
        is_heading, level = detect_heading_by_text(line_text)
        blocks.append(RawBlock(text=line_text, page_number=1, is_heading=is_heading, heading_level=level))

    return blocks, 1
