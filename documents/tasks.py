from celery import shared_task

from .processing.pipeline import process_document


@shared_task(name='documents.process_document')
def process_document_task(document_id):
    process_document(document_id)
