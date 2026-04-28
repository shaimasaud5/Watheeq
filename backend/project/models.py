# project/models.py
# ------------------
# Core data models for the Watheeq project.
#
# DOCUMENT LIFECYCLE:
#   DRAFT      → created project document, no schema yet
#   EXTRACTED  → task 3 (extraction and filling schema) sent filled_schema via set-schema/
#   GENERATED  → .docx built, waiting for user review (in pending_file)
#   APPROVED   → user approved, file moved to generated_file permanently
#   FAILED     → generation error
#
# ONE PROJECT CAN HAVE MULTIPLE DOCUMENTS:
#   project=1, doc_type=BRD → one row
#   project=1, doc_type=MOM → another row
#   Distinguished by doc_type field, not separate tables.

from django.db import models
from django.conf import settings


class Project(models.Model):
    owner = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects" )   
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Meeting(models.Model):
    project    = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="meetings")
    title      = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.project.name} — {self.title}"


class Document(models.Model):

    STATUS_CHOICES = [
        ("DRAFT",      "Draft"),
        ("EXTRACTED",  "Extracted"),
        ("GENERATED",  "Generated"),
        ("APPROVED",   "Approved"),
        ("FAILED",     "Failed"),
    ]

    DOC_TYPE_CHOICES = [
        ("BRD", "Business Requirements Document"),
        ("MOM", "Minutes of Meeting"),
        ("SRS", "Software Requirements Specification"),
    ]

    # ── Core fields ───────────────────────────────────────────────
    project  = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(
        max_length=10,
        choices=DOC_TYPE_CHOICES,
        default="BRD",
    )

    # ── Schema & content ──────────────────────────────────────────
    # extracted_json: filled by task3 via set-schema/ endpoint
    # content:        plain-text version stored after generation
    extracted_json = models.JSONField(null=True, blank=True)
    content        = models.TextField(blank=True, default="")

    # ── Files ─────────────────────────────────────────────────────
    # generated_file: the APPROVED final .docx shown in Documents tab
    # pending_file:   temporary .docx waiting for user Approve/Regenerate
    #                 deleted after approve or overwritten on regenerate
    generated_file = models.FileField(
        upload_to="documents/",
        null=True,
        blank=True,
    )
    pending_file = models.FileField(
        upload_to="pending/",
        null=True,
        blank=True,
    )

    # ── Status & approval ─────────────────────────────────────────
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="True after user clicks Approve in the review popup.",
    )

    # ── Generation metadata ───────────────────────────────────────
    # Stores: model name, temperature, elapsed_seconds, error message
    meta = models.JSONField(null=True, blank=True)

    # ── Timestamps ────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        # One BRD and one MOM per project — prevents duplicates
        unique_together = [("project", "doc_type")]

    def __str__(self):
        return f"{self.project.name} — {self.doc_type} [{self.status}]"