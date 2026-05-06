# generation/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from extract.models import Extraction
from .models import GeneratedDocument
from .services.orchestrator import GenerationError, generate_brd_from_schema, generate_mom_from_schema


@receiver(post_save, sender=Extraction)
def create_and_generate_document(sender, instance, created, **kwargs):
    """
    بعد اكتمال مرحلة Extraction (status = completed):
    1. ينشئ GeneratedDocument
    2. يولّد الـ .docx مباشرة
    بدون تدخل المستخدم.
    """
    
    if instance.status != Extraction.STATUS_COMPLETED:
        return


    document = instance.document

    # ننشئ GeneratedDocument ونربطه بالـ Extraction
    gen_doc, _ = GeneratedDocument.objects.get_or_create(
        document=document,
        defaults={"extraction": instance, "status": "IN_PROGRESS"}  # ← هنا فقط التعديل
    )

    # ── معلومات غلاف الوثيقة ────────────────────────────────────
    # هذه المعلومات تأتي من قاعدة البيانات مباشرة — لا من السكيما
    # date    = تاريخ إنشاء الوثيقة
    # author  = اسم صاحب المشروع
    # version = 1.0 دائماً عند التوليد الأول
    cover_meta = {
        "date":    document.created_at.strftime("%B %d, %Y"),
        "author":  document.project.owner.username if document.project.owner else "—",
        "version": "1.0",
    }

    # نولّد الـ .docx مباشرة
    try:
        # بداية التوليد (loading للبار)
        gen_doc.status = "IN_PROGRESS"
        gen_doc.save(update_fields=["status"])

        if document.doc_type == "BRD":
            text, path, meta = generate_brd_from_schema(
                instance.filled_schema,
                document_id   = document.id,
                project_name  = document.project.name or "",
                output_subdir = "pending",
                cover_meta    = cover_meta,
            )
        else:
            text, path, meta = generate_mom_from_schema(
                instance.filled_schema,
                document_id   = document.id,
                project_name  = document.project.name or "",
                output_subdir = "pending",
                cover_meta    = cover_meta,
            )

        meta["regenerate_count"]  = 0
        gen_doc.content           = text
        gen_doc.pending_file.name = path
        gen_doc.status            = "GENERATED"
        gen_doc.meta              = meta
        gen_doc.save(update_fields=["content", "pending_file", "status", "meta"])

    except Exception as e:
        gen_doc.status = "FAILED"
        gen_doc.meta   = {"error": str(e)}
        gen_doc.save(update_fields=["status", "meta"])