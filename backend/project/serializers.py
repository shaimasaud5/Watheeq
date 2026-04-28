from rest_framework import serializers
from django.db import transaction
from .models import Project, Meeting, Document
from transcript.models import Transcript


SUPPORTED_DOC_TYPES = ["BRD", "MOM"]


class CreateProjectSerializer(serializers.Serializer):
    """
    Creates a full project setup in one atomic transaction:
        Project + Meeting + Document + Transcript

    Returns document_id — this ID must be passed to girl 3 (extract task)
    so she can POST the filled schema back to:
        /api/generation/documents/{document_id}/set-schema/

    Supported document_type values: BRD, MOM, SRS
    """
    project_name   = serializers.CharField(max_length=200)
    meeting_title  = serializers.CharField(max_length=200)
    document_type  = serializers.ChoiceField(choices=SUPPORTED_DOC_TYPES)
    transcript_raw = serializers.CharField()

    @transaction.atomic
    def create(self, validated_data):
        request   = self.context["request"]
        doc_type  = validated_data["document_type"].upper()

        project = Project.objects.create(
            owner=request.user,
            name=validated_data["project_name"],
        )

        meeting = Meeting.objects.create(
            project=project,
            title=validated_data["meeting_title"],
        )

        document = Document.objects.create(
            project=project,
            doc_type=doc_type,
            content="",
        )

        Transcript.objects.create(
            meeting=meeting,
            raw_text=validated_data["transcript_raw"],
            processed_text=validated_data["transcript_raw"],  # filled by task 1
        )

        return {
            "project_id":  project.id,
            "meeting_id":  meeting.id,
            "document_id": document.id,
            "doc_type":    document.doc_type,
        }