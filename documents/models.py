import uuid

from django.conf import settings
from django.db import models


def document_upload_path(instance, filename):
    return f'orgs/{instance.organization_id}/documents/{instance.id}/{filename}'


class Document(models.Model):
    class Status(models.TextChoices):
        UPLOADED = 'UPLOADED', 'Uploaded'
        PROCESSING = 'PROCESSING', 'Processing'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'

    class FileType(models.TextChoices):
        PDF = 'PDF', 'PDF'
        DOCX = 'DOCX', 'DOCX'
        TXT = 'TXT', 'TXT'
        IMAGE = 'IMAGE', 'Image'

    class Category(models.TextChoices):
        CONTRACT = 'CONTRACT', 'Contract'
        REGULATION = 'REGULATION', 'Regulation'
        POLICY = 'POLICY', 'Policy'
        REPORT = 'REPORT', 'Report'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'core.Organization', on_delete=models.CASCADE, related_name='documents',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='uploaded_documents',
    )
    file = models.FileField(upload_to=document_upload_path, max_length=512)
    original_filename = models.CharField(max_length=512)
    file_type = models.CharField(max_length=20, choices=FileType.choices)
    mime_type = models.CharField(max_length=128, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    error_message = models.TextField(blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, blank=True)
    entities = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.original_filename


class Chunk(models.Model):
    """A paragraph/section-level slice of a document's extracted text,
    tagged with enough structure info (page, heading, hierarchy path) to
    cite back to the exact source location."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_heading = models.CharField(max_length=512, blank=True)
    hierarchy_path = models.CharField(max_length=1024, blank=True)
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document_id', 'index']
        constraints = [
            models.UniqueConstraint(
                fields=['document', 'index'], name='unique_chunk_index_per_document',
            )
        ]

    def __str__(self):
        return f'{self.document_id}#{self.index}'
