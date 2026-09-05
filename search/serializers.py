from rest_framework import serializers


class SearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000, trim_whitespace=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)

    def validate_query(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value


class SearchResultSerializer(serializers.Serializer):
    chunk_id = serializers.CharField()
    document_id = serializers.CharField()
    original_filename = serializers.CharField()
    page_number = serializers.IntegerField(allow_null=True)
    section_heading = serializers.CharField(allow_blank=True)
    hierarchy_path = serializers.CharField(allow_blank=True)
    text = serializers.CharField()
    score = serializers.FloatField()
