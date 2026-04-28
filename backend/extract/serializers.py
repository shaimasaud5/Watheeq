from rest_framework import serializers


class DynamicExtractSerializer(serializers.Serializer):
    doc_type = serializers.CharField()
    transcript = serializers.CharField()
    template_text = serializers.CharField(required=False, allow_blank=True)


class ProcessingRequestSerializer(serializers.Serializer):
    doc_type = serializers.CharField()
    transcript_id = serializers.IntegerField()
    template_file = serializers.FileField(required=False)
