"""PaddleOCR wrapper.

The documents this platform ingests mix Uzbek (Latin script), Russian
(Cyrillic), and English. PaddleOCR ships separate language models, so
rather than guessing a single language per document we run every
configured language pack against the page and keep whichever produced the
most (confidently) recognized text — a cheap stand-in for real language
detection that's good enough for an MVP.
"""

from functools import lru_cache
from io import BytesIO

from django.conf import settings
from PIL import Image

_MIN_CONFIDENCE = 0.5


@lru_cache(maxsize=None)
def _get_engine(lang: str):
    from paddleocr import PaddleOCR

    return PaddleOCR(lang=lang, use_angle_cls=True, show_log=False)


def _run_single_language(image, lang: str) -> tuple[list[str], float]:
    engine = _get_engine(lang)
    result = engine.ocr(image, cls=True)

    lines: list[str] = []
    confidences: list[float] = []
    for page_result in result or []:
        for entry in page_result or []:
            text, confidence = entry[1]
            if confidence >= _MIN_CONFIDENCE and text.strip():
                lines.append(text.strip())
                confidences.append(confidence)

    score = sum(confidences)  # roughly: more, higher-confidence text wins
    return lines, score


def run_ocr(image_bytes: bytes) -> list[str]:
    """Runs OCR across all configured languages and returns the text lines
    (in reading order) from whichever language pack scored best."""
    import numpy as np

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(image)

    best_lines: list[str] = []
    best_score = -1.0

    for lang in settings.OCR_LANGUAGES:
        lines, score = _run_single_language(image_array, lang)
        if score > best_score:
            best_lines, best_score = lines, score

    return best_lines
