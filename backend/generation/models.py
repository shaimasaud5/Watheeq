from django.db import models
from project.models import Document
from extract.models import Extraction


class GeneratedDocument(models.Model):

    STATUS_CHOICES = [
    ("DRAFT", "Draft"),
    ("IN_PROGRESS", "In Progress"),
    ("GENERATED", "Generated"),
    ("APPROVED", "Approved"),
    ("FAILED", "Failed"),
]

    
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="generated",
    )

    extraction = models.ForeignKey(
        Extraction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
    )


    content = models.TextField(blank=True, default="")

    pending_file = models.FileField(
        upload_to="pending/",
        null=True,
        blank=True,
    )

    generated_file = models.FileField(
        upload_to="documents/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    is_approved = models.BooleanField(default=False)

    meta = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    #updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document.project.name} — {self.document.doc_type} [{self.status}]"