from rest_framework import serializers


class ConversationTurnSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField()


class AskQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000, trim_whitespace=True)
    conversation_history = ConversationTurnSerializer(many=True, required=False, default=list)
    document_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_question(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value


class SourceSerializer(serializers.Serializer):
    index = serializers.IntegerField()
    chunk_id = serializers.CharField()
    document_id = serializers.CharField()
    original_filename = serializers.CharField()
    page_number = serializers.IntegerField(allow_null=True)
    section_heading = serializers.CharField(allow_blank=True)
    hierarchy_path = serializers.CharField(allow_blank=True)
    text = serializers.CharField()
    score = serializers.FloatField()


class AskAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField()
    confident = serializers.BooleanField()
    citations = SourceSerializer(many=True)
    sources = SourceSerializer(many=True)
    follow_up_questions = serializers.ListField(child=serializers.CharField())
