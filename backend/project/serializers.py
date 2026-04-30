from rest_framework import serializers
from django.db import transaction
from .models import Project, Meeting, Document


class CreateProjectSerializer(serializers.Serializer):
    """
    Validates incoming data from the New Project & Meeting Setup form,
    then creates Project, Meeting, and Document records in the database.
    """

    # ─── Project Information ───────────────────────────────────────
    # Required fields
    project_name = serializers.CharField(max_length=200)
    client       = serializers.CharField(max_length=200)
    manager      = serializers.CharField(max_length=200)

    # Optional fields
    domain       = serializers.CharField(max_length=200, required=False, default="")
    project_type = serializers.CharField(max_length=200, required=False, default="")
    target_user  = serializers.CharField(max_length=200, required=False, default="")

    # Only BRD and MOM are supported
    document_type = serializers.ChoiceField(choices=["BRD", "MOM"])

    #Optional template file (PDF or DOCX),
    template_file = serializers.FileField(required=False, allow_null=True)

    # ─── Meeting Setup ─────────────────────────────────────────────
    meeting_title = serializers.CharField(max_length=200)
    platform      = serializers.ChoiceField(choices=["zoom", "teams", "google_meet"])
    meeting_link  = serializers.URLField()

    @transaction.atomic
    def create(self, validated_data):
        """
        Creates Project, Meeting, and Document in a single atomic transaction.
        If any step fails, all changes are rolled back.
        """
        request = self.context["request"]

        # 1. Create the project with all provided information
        project = Project.objects.create(
        owner=request.user if request.user.is_authenticated else None,
        name=validated_data["project_name"],
        client=validated_data["client"],
        manager=validated_data["manager"],
        domain=validated_data.get("domain", ""),
        project_type=validated_data.get("project_type", ""),
        target_user=validated_data.get("target_user", ""),
)

        # 2. Create the meeting linked to this project
        meeting = Meeting.objects.create(
            project      = project,
            title        = validated_data["meeting_title"],
            platform     = validated_data["platform"],
            meeting_link = validated_data["meeting_link"],
        )

        # 3. Create an empty document — content will be filled later by the generation pipeline
        document = Document.objects.create(
            project  = project,
            doc_type = validated_data["document_type"],
            template_file = validated_data.get("template_file", None),
        )

        return {
            "project_id" : project.id,
            "meeting_id" : meeting.id,
            "document_id": document.id,
            "doc_type"   : document.doc_type,
        }