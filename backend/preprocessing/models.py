from django.db import models
from project.models import Meeting


class Transcript(models.Model):

    SOURCE_HYBRID = "hybrid"
    STATUS_PENDING   = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED    = "failed"

    # Each meeting has only one transcript
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name="transcript"
    )

    # Source is hybrid (Recall + Whisper)
    source = models.CharField(
        max_length=20,
        choices=[
            (SOURCE_HYBRID, "hybrid"),
        ],
        default= SOURCE_HYBRID 
    )
    status = models.CharField(
        max_length=20,
        choices=[
            (STATUS_PENDING,   "Pending"),
            (STATUS_COMPLETED, "Completed"),
            (STATUS_FAILED,    "Failed"),
        ],
        default=STATUS_PENDING
    )

    # Stores the meeting link
    meeting_link = models.URLField(blank=True, null=True)

    # Final structured output after preprocessing
    processed_json = models.JSONField(blank=True, null=True)

    # Timestamp when the transcript record is created
    created_at = models.DateTimeField(auto_now_add=True)

    # Timestamp when preprocessing is completed
    processed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.meeting.project.name} - Transcript ({self.source})"
    


