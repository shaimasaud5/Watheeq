from django.db import models
from project.models import Document
from processing.models import TranscriptChunk


class Extraction(models.Model):
    """
    Represents the extraction stage (Task 3).

    Stores the filled_schema generated from transcript chunks
    after processing (chunking, translation, embeddings).
    Used as input for the generation stage.
    """

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="extraction",
    )

    chunk = models.ForeignKey(
        TranscriptChunk,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extractions",
    )


    filled_schema = models.JSONField()


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    error_message = models.TextField(blank=True, default="")


    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.doc_type} Extraction — {self.document.project.name}"