import logging

from django.db import transaction

from ..models import Chunk, Document
from .blocks import assign_hierarchy
from .chunking import chunk_blocks
from .extractors import extract_docx, extract_image, extract_pdf, extract_txt
from .intelligence import analyze_document
from .vector_store import delete_document_vectors, upsert_chunks

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    pass


def _extract(document: Document) -> tuple[list, int]:
    file_type = document.file_type

    # Read via the storage API (not `.file.path`) so this works against
    # any backend, including MinIO/S3 where there is no local path.
    with document.file.open('rb') as f:
        file_bytes = f.read()

    if file_type == Document.FileType.PDF:
        blocks, page_count, _used_ocr = extract_pdf(file_bytes)
    elif file_type == Document.FileType.DOCX:
        blocks, page_count = extract_docx(file_bytes)
    elif file_type == Document.FileType.TXT:
        blocks, page_count = extract_txt(file_bytes)
    elif file_type == Document.FileType.IMAGE:
        blocks, page_count = extract_image(file_bytes)
    else:
        raise ProcessingError(f'Unsupported file type: {file_type}')

    if not blocks:
        raise ProcessingError('No text could be extracted from this document.')

    return blocks, page_count


def process_document(document_id) -> None:
    """Runs the full Phase 2 pipeline for one document: extract text
    (with OCR fallback for scanned PDFs/images), detect structure, chunk,
    and persist. Updates the document's status throughout."""
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.warning('process_document called for missing document %s', document_id)
        return

    document.status = Document.Status.PROCESSING
    document.error_message = ''
    document.save(update_fields=['status', 'error_message', 'updated_at'])

    try:
        raw_blocks, page_count = _extract(document)
        enriched_blocks = assign_hierarchy(raw_blocks)
        chunk_dicts = chunk_blocks(enriched_blocks)

        if not chunk_dicts:
            raise ProcessingError('Document text was empty after processing.')

        with transaction.atomic():
            document.chunks.all().delete()
            created_chunks = Chunk.objects.bulk_create(
                Chunk(
                    document=document,
                    index=c['index'],
                    page_number=c['page_number'],
                    section_heading=c['section_heading'],
                    hierarchy_path=c['hierarchy_path'],
                    text=c['text'],
                    token_count=c['token_count'],
                )
                for c in chunk_dicts
            )

        # Outside the DB transaction: Qdrant isn't part of it, and a
        # document is only really "ready" once it's searchable.
        delete_document_vectors(document.id)
        upsert_chunks(document, created_chunks)

        # Classification + entity extraction are supplementary metadata,
        # not required for the document to be searchable or askable — a
        # failure here must never fail the whole document.
        try:
            analyze_document(document)
        except Exception:  # noqa: BLE001
            logger.exception('Document analysis failed for %s (non-fatal)', document_id)

        document.page_count = page_count
        document.status = Document.Status.READY
        document.save(update_fields=['page_count', 'status', 'updated_at'])

    except Exception as exc:  # noqa: BLE001 - surface any failure as a FAILED document
        logger.exception('Failed to process document %s', document_id)
        document.status = Document.Status.FAILED
        document.error_message = str(exc)[:2000]
        document.save(update_fields=['status', 'error_message', 'updated_at'])
