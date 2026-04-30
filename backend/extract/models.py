# extract/models.py
from django.db import models
from project.models import Document
from processing.models import TranscriptChunk


class Extraction(models.Model):
    """
    جدول مهمة 3 — يحفظ الـ filled_schema المستخرجة.

    يخدم مهمتين:
    - مهمة 2: ترسل له الـ chunks عند استدعاء مهمة 3
              chunk → transcript → chunks كلها
    - مهمة 4: تسحب filled_schema عبر document.extraction
    """

    # OneToOne — كل وثيقة لها استخراج واحد فقط
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name="extraction",
    )

    # مرجع لأي chunk من مهمة 2
    # عبره نعرف الترانسكريبت وبالتالي جميع الـ chunks
    chunk = models.ForeignKey(
        TranscriptChunk,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extractions",
    )

    # السكيما المستخرجة — مدخل مهمة 4
    filled_schema = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.doc_type} Extraction — {self.document.project.name}"
