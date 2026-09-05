from functools import lru_cache

from django.conf import settings

from .embeddings import embed_texts


@lru_cache(maxsize=1)
def get_client():
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)


def ensure_collection() -> None:
    from qdrant_client import models as qmodels

    client = get_client()
    collection_name = settings.QDRANT_COLLECTION_NAME
    existing = {c.name for c in client.get_collections().collections}
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=settings.EMBEDDING_DIMENSION, distance=qmodels.Distance.COSINE,
            ),
        )


def upsert_chunks(document, chunks) -> None:
    """Embeds and upserts one document's chunks. `chunks` are Chunk
    instances that already have their `id` set (true even pre-save, since
    the primary key is a client-side UUID default)."""
    if not chunks:
        return

    from qdrant_client import models as qmodels

    ensure_collection()
    client = get_client()

    vectors = embed_texts([c.text for c in chunks])
    points = [
        qmodels.PointStruct(
            id=str(chunk.id),
            vector=vector,
            payload={
                'document_id': str(document.id),
                'organization_id': str(document.organization_id),
                'chunk_index': chunk.index,
                'page_number': chunk.page_number,
                'section_heading': chunk.section_heading,
                'hierarchy_path': chunk.hierarchy_path,
                'text': chunk.text,
                'original_filename': document.original_filename,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)


def delete_document_vectors(document_id) -> None:
    from qdrant_client import models as qmodels

    ensure_collection()
    client = get_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[qmodels.FieldCondition(key='document_id', match=qmodels.MatchValue(value=str(document_id)))]
            )
        ),
    )


def search(query_vector: list[float], organization_id, limit: int = 10, document_id=None) -> list:
    """`document_id`, when given, scopes retrieval to one document — e.g.
    the Document Viewer's "Ask about this document" (Phase 5), as opposed
    to organization-wide Ask AI / Search."""
    from qdrant_client import models as qmodels

    ensure_collection()
    client = get_client()

    must = [qmodels.FieldCondition(key='organization_id', match=qmodels.MatchValue(value=str(organization_id)))]
    if document_id is not None:
        must.append(qmodels.FieldCondition(key='document_id', match=qmodels.MatchValue(value=str(document_id))))

    response = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=qmodels.Filter(must=must),
        limit=limit,
        with_payload=True,
    )
    return response.points
