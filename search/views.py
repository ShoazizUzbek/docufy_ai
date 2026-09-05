from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.processing.embeddings import embed_query
from documents.processing.vector_store import search as search_chunks

from .serializers import SearchQuerySerializer, SearchResultSerializer


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query_serializer = SearchQuerySerializer(data=request.data)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data['query']
        limit = query_serializer.validated_data['limit']

        query_vector = embed_query(query)
        points = search_chunks(query_vector, request.user.organization_id, limit=limit)

        results = [
            {
                'chunk_id': str(point.id),
                'document_id': point.payload.get('document_id', ''),
                'original_filename': point.payload.get('original_filename', ''),
                'page_number': point.payload.get('page_number'),
                'section_heading': point.payload.get('section_heading', ''),
                'hierarchy_path': point.payload.get('hierarchy_path', ''),
                'text': point.payload.get('text', ''),
                'score': point.score,
            }
            for point in points
        ]

        return Response(SearchResultSerializer(results, many=True).data)
