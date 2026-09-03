import os

from rest_framework import serializers

from .models import Document

EXTENSION_TO_FILE_TYPE = {
    '.pdf': Document.FileType.PDF,
    '.docx': Document.FileType.DOCX,
    '.txt': Document.FileType.TXT,
    '.png': Document.FileType.IMAGE,
    '.jpg': Document.FileType.IMAGE,
    '.jpeg': Document.FileType.IMAGE,
    '.tif': Document.FileType.IMAGE,
    '.tiff': Document.FileType.IMAGE,
    '.bmp': Document.FileType.IMAGE,
}


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'original_filename', 'file_type', 'mime_type', 'file_size',
            'status', 'error_message', 'page_count', 'uploaded_by_email',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Document
        fields = ['id', 'file']
        read_only_fields = ['id']

    def validate_file(self, value):
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in EXTENSION_TO_FILE_TYPE:
            allowed = ', '.join(sorted(EXTENSION_TO_FILE_TYPE))
            raise serializers.ValidationError(f'Unsupported file type "{ext}". Allowed: {allowed}')
        return value

    def create(self, validated_data):
        file_obj = validated_data['file']
        ext = os.path.splitext(file_obj.name)[1].lower()
        request = self.context['request']
        document = Document.objects.create(
            organization=request.user.organization,
            uploaded_by=request.user,
            file=file_obj,
            original_filename=file_obj.name,
            file_type=EXTENSION_TO_FILE_TYPE[ext],
            mime_type=getattr(file_obj, 'content_type', '') or '',
            file_size=file_obj.size,
            status=Document.Status.UPLOADED,
        )
        return document
