"""BGE-M3 embeddings.

BGE-M3 is multilingual (100+ languages, including Uzbek, Russian, and
English), so unlike OCR there's no need to pick a language per document —
one model handles the mix. It needs no special instruction prefix for
either passages or queries (unlike some earlier BGE models), so the same
`embed_texts` powers both indexing and querying.
"""

from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
