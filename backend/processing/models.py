from django.db import models
from preprocessing.models import Transcript


class TranscriptChunk(models.Model):

    class StatusChoices(models.TextChoices):
        PENDING   = "pending",   "Pending"
        COMPLETED = "completed", "Completed"
        FAILED    = "failed",    "Failed"

    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name="chunks"
    )

    chunk_index           = models.PositiveIntegerField()
    chunk_text            = models.TextField()
    semantic_english_text = models.TextField(blank=True, default="")
    embedding             = models.JSONField(blank=True, null=True)
    status                = models.CharField(
                                max_length=20,
                                choices=StatusChoices.choices,
                                default=StatusChoices.PENDING
                            )
    error_message         = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["chunk_index"]

    def __str__(self):
        return f"Transcript {self.transcript_id} - Chunk {self.chunk_index} [{self.status}]"
    
# 
    