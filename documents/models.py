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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.original_filename
