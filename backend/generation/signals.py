# generation/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from extract.models import Extraction
from .models import GeneratedDocument
from .services.orchestrator import GenerationError, generate_brd_from_schema, generate_mom_from_schema


@receiver(post_save, sender=Extraction)
def create_and_generate_document(sender, instance, created, **kwargs):
    """
    After the Extraction stage is completed (status = completed):
    1. Creates a GeneratedDocument
    2. Generates the .docx file directly
    without user intervention.
    """
    
    if instance.status != Extraction.STATUS_COMPLETED:
        return


    document = instance.document

    # Create a GeneratedDocument and link it to the Extraction
    gen_doc, _ = GeneratedDocument.objects.get_or_create(
        document=document,
        defaults={"extraction": instance, "status": "IN_PROGRESS"}  # ← هنا فقط التعديل
    )

    # ── Document cover information ─────────────────────────────
    # This information comes directly from the database — not from the schema
    # date    = document creation date
    # author  = project owner name
    # version = always 1.0 on the first generation
    cover_meta = {
        "date":    document.created_at.strftime("%B %d, %Y"),
        "author":  document.project.owner.username if document.project.owner else "—",
        "version": "1.0",
    }

     # Generate the .docx file directly
    try:
        # Start generation process (loading state for the progress bar)
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