from django.db import models
from django.conf import settings


class Project(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=200)
    client = models.CharField(max_length=200)
    manager = models.CharField(max_length=200)
    domain = models.CharField(max_length=200, blank=True, default="")
    project_type = models.CharField(max_length=200, blank=True, default="")
    target_user = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Meeting(models.Model):
    # Stores meeting details + Recall bot integration + meeting lifecycle status

    PLATFORM_ZOOM = "zoom"
    PLATFORM_TEAMS = "teams"
    PLATFORM_MEET = "google_meet"

    PLATFORM_CHOICES = [
        (PLATFORM_ZOOM, "Zoom"),
        (PLATFORM_TEAMS, "Microsoft Teams"),
        (PLATFORM_MEET, "Google Meet"),
    ]

    # Meeting lifecycle status (used for frontend progress bar)
    STATUS_CREATED = "created"
    STATUS_JOINING = "joining"
    STATUS_IN_MEETING = "in_meeting"
    STATUS_ENDED = "ended"
    STATUS_POST_MEETING = "post_meeting"
    STATUS_TRANSCRIBING = "transcribing"
    STATUS_TRANSCRIBED = "transcribed"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_JOINING, "Joining"),
        (STATUS_IN_MEETING, "In Meeting"),
        (STATUS_ENDED, "Ended"),
        (STATUS_POST_MEETING, "Post Meeting"),
        (STATUS_TRANSCRIBING, "Transcribing"),
        (STATUS_TRANSCRIBED, "Transcribed"),
    ]

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="meeting"
    )
    title = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    meeting_link = models.URLField()

    # Recall.ai bot ID to identify webhook events for this meeting
    recall_bot_id = models.CharField(max_length=200, blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project.name} - {self.title}"


class Document(models.Model):
    # Stores requested document type and optional user template

    DOC_TYPES = [
        ("BRD", "BRD"),
        ("MOM", "MOM"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    doc_type = models.CharField(max_length=3, choices=DOC_TYPES)

    # Optional template file uploaded by the user (PDF or DOCX)
    template_file = models.FileField(
        upload_to="templates/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "doc_type")

    def __str__(self):
        return f"{self.project.name} - {self.doc_type}"