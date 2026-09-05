from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .rag import answer_question
from .serializers import AskAnswerSerializer, AskQuestionSerializer


class AskAIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query_serializer = AskQuestionSerializer(data=request.data)
        query_serializer.is_valid(raise_exception=True)

        result = answer_question(
            question=query_serializer.validated_data['question'],
            organization_id=request.user.organization_id,
            conversation_history=query_serializer.validated_data['conversation_history'],
            document_id=query_serializer.validated_data['document_id'],
        )

        return Response(AskAnswerSerializer(result).data)
