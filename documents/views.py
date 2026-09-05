from itertools import groupby

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Document
from .serializers import DocumentPageSerializer, DocumentSerializer, DocumentUploadSerializer
from .tasks import process_document_task


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return Document.objects.filter(organization=self.request.user.organization)

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer

    def perform_create(self, serializer):
        document = serializer.save()
        process_document_task.delay(str(document.id))

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        document = Document.objects.get(pk=response.data['id'])
        response.data = DocumentSerializer(document).data
        return response

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Full extracted text, grouped by page — what the Document Viewer
        and the citation-preview panel render (not a rendering of the
        original file itself; see README for why)."""
        document = self.get_object()
        chunks = document.chunks.order_by('page_number', 'index')
        pages = [
            {'page_number': page_number, 'chunks': list(group)}
            for page_number, group in groupby(chunks, key=lambda c: c.page_number)
        ]
        return Response(DocumentPageSerializer(pages, many=True).data)
