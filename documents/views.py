from rest_framework import viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer


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
        serializer.save()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        document = Document.objects.get(pk=response.data['id'])
        response.data = DocumentSerializer(document).data
        return response
