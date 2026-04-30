# generation/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from extract.models import Extraction
from .models import GeneratedDocument
from .services.orchestrator import GenerationError, generate_brd_from_schema, generate_mom_from_schema


@receiver(post_save, sender=Extraction)
def create_and_generate_document(sender, instance, created, **kwargs):
    """
    بعد حفظ Extraction من مهمة 3 تلقائياً:
    1. ينشئ GeneratedDocument
    2. يولّد الـ .docx مباشرة
    بدون تدخل المستخدم.
    """
    if not created:
        return

    document = instance.document

    # ننشئ GeneratedDocument ونربطه بالـ Extraction
    gen_doc, _ = GeneratedDocument.objects.get_or_create(
        document=document,
        defaults={"extraction": instance, "status": "EXTRACTED"}
    )

    # نولّد الـ .docx مباشرة
    try:
        if document.doc_type == "BRD":
            text, path, meta = generate_brd_from_schema(
                instance.filled_schema,
                document_id=document.id,
                project_name=document.project.name or "",
                output_subdir="pending",
            )
        else:
            text, path, meta = generate_mom_from_schema(
                instance.filled_schema,
                document_id=document.id,
                project_name=document.project.name or "",
                output_subdir="pending",
            )

        meta["regenerate_count"]   = 0
        gen_doc.content            = text
        gen_doc.pending_file.name  = path
        gen_doc.status             = "GENERATED"
        gen_doc.meta               = meta
        gen_doc.save(update_fields=["content", "pending_file", "status", "meta"])

    except Exception as e:
        gen_doc.status = "FAILED"
        gen_doc.meta   = {"error": str(e)}
        gen_doc.save(update_fields=["status", "meta"])