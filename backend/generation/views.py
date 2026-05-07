# generation/views.py
from django.core.files.base import File
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from project.models import Project, Document
from processing.models import TranscriptChunk
from extract.models import Extraction
from extract.extractor import extract_brd, extract_mom

from .models import GeneratedDocument
from .services.orchestrator import GenerationError, generate_brd_from_schema, generate_mom_from_schema

MAX_REGENERATE_ATTEMPTS = 3

class GenerateNewDocumentAfterProjectAPIView(APIView):
    """
    New document generation after the project was already created.

    Used when the user already generated and approved one document type
    (BRD or MOM), then clicks:
        + Generate New Document

    This API does NOT repeat:
    - Meeting bot
    - Preprocessing
    - Processing
    - Chunking
    - Embeddings

    It starts only from:
    Extraction -> Generation
    """

    permission_classes = [AllowAny]

    def post(self, request, project_id):
        document_type = request.data.get("document_type")

        if not document_type:
            return Response({"error": "document_type is required. Use BRD or MOM."}, status=400)

        document_type = document_type.upper()

        if document_type not in ["BRD", "MOM"]:
            return Response({"error": "Invalid document_type. Use BRD or MOM."}, status=400)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found."}, status=404)

        # Prevent duplicate document type for the same project
        if Document.objects.filter(project=project, doc_type=document_type).exists():
            return Response({
                "error": f"{document_type} already exists for this project."
            }, status=400)

        # Only allow the remaining document type
        existing_types = set(project.documents.values_list("doc_type", flat=True))

        if len(existing_types) >= 2:
            return Response({
                "error": "Both BRD and MOM already exist for this project."
            }, status=400)

        allowed_remaining_types = {"BRD", "MOM"} - existing_types

        if document_type not in allowed_remaining_types:
            return Response({
                "error": f"You can only generate the remaining document type: {list(allowed_remaining_types)}"
            }, status=400)

        # Get transcript from the existing meeting
        try:
            transcript = project.meeting.transcript
        except Exception:
            return Response({
                "error": "No transcript found for this project. Preprocessing must be completed first."
            }, status=400)

        # Reuse completed chunks from Processing stage
        chunks = list(
            TranscriptChunk.objects.filter(
                transcript=transcript,
                status="completed",
            ).order_by("chunk_index").values("semantic_english_text", "embedding")
        )

        if not chunks:
            return Response({
                "error": "No completed chunks found. Processing must be completed first."
            }, status=400)

        first_chunk = TranscriptChunk.objects.filter(
            transcript=transcript,
            status="completed",
        ).order_by("chunk_index").first()

        # Create the new Document only after all checks pass
        document = Document.objects.create(
            project=project,
            doc_type=document_type,
        )

        # Create extraction record for the new document
        extraction = Extraction.objects.create(
            document=document,
            chunk=first_chunk,
            filled_schema={},
            status=Extraction.STATUS_IN_PROGRESS,
            error_message="",
        )

        try:
            # Run extraction only for the new document type
            if document_type == "BRD":
                filled_schema = extract_brd(chunks)
            else:
                filled_schema = extract_mom(chunks)

            extraction.filled_schema = filled_schema
            extraction.status = Extraction.STATUS_COMPLETED
            extraction.error_message = ""
            extraction.save(update_fields=["filled_schema", "status", "error_message"])

        except Exception as e:
            extraction.status = Extraction.STATUS_FAILED
            extraction.error_message = str(e)
            extraction.save(update_fields=["status", "error_message"])

            return Response({
                "error": "Extraction failed.",
                "details": str(e),
                "document_id": document.id,
            }, status=400)

        # Create GeneratedDocument and start generation
        gen_doc = GeneratedDocument.objects.create(
            document=document,
            extraction=extraction,
            status="IN_PROGRESS",
            is_approved=False,
            meta={},
        )

        cover_meta = {
            "date": document.created_at.strftime("%B %d, %Y"),
            "author": project.owner.username if project.owner else "—",
            "version": "1.0",
        }

        try:
            if document_type == "BRD":
                text, path, meta = generate_brd_from_schema(
                    extraction.filled_schema,
                    document_id=document.id,
                    project_name=project.name or "",
                    output_subdir="pending",
                    cover_meta=cover_meta,
                )
            else:
                text, path, meta = generate_mom_from_schema(
                    extraction.filled_schema,
                    document_id=document.id,
                    project_name=project.name or "",
                    output_subdir="pending",
                    cover_meta=cover_meta,
                )

        except GenerationError as e:
            gen_doc.status = "FAILED"
            gen_doc.meta = {"error": str(e)}
            gen_doc.save(update_fields=["status", "meta"])

            return Response({
                "error": "Generation failed.",
                "details": str(e),
                "document_id": document.id,
            }, status=400)

        gen_doc.content = text
        gen_doc.pending_file.name = path
        gen_doc.status = "GENERATED"
        gen_doc.is_approved = False
        gen_doc.meta = meta
        gen_doc.save(update_fields=[
            "content",
            "pending_file",
            "status",
            "is_approved",
            "meta",
        ])

        return Response({
            "status": "ok",
            "message": f"New {document_type} document generated successfully.",
            "project_id": project.id,
            "document_id": document.id,
            "document_type": document.doc_type,
            "generated_status": gen_doc.status,
            "pending_url": gen_doc.pending_file.url if gen_doc.pending_file else None,
        })

class RegenerateDocumentAPIView(APIView):
    """
    المستخدم يضغط Regenerate →
    يعيد التوليد من نفس الـ schema بحد أقصى 3 مرات.
    مهمة 3 لا تُعاد.
    """
    permission_classes = [AllowAny]

    def post(self, request, document_id):
        try:
            gen_doc = GeneratedDocument.objects.get(document_id=document_id)
        except GeneratedDocument.DoesNotExist:
            return Response({"error": "No generated document found."}, status=400)

        document = gen_doc.document

        if gen_doc.status not in ("GENERATED", "FAILED"):
            return Response(
                {"error": f"Cannot regenerate from status: {gen_doc.status}"},
                status=400
            )

        # كم مرة أعاد المستخدم التوليد
        count = int((gen_doc.meta or {}).get("regenerate_count", 0))

        if count >= MAX_REGENERATE_ATTEMPTS:
            return Response({
                "error":   "limit_reached",
                "message": f"Used all {MAX_REGENERATE_ATTEMPTS} attempts. Please approve.",
            }, status=400)

        # ── معلومات غلاف الوثيقة ────────────────────────────────
        # version يتغير مع كل regenerate: 1.0 → 1.1 → 1.2 → 1.3
        new_count  = count + 1
        cover_meta = {
            "date":    document.created_at.strftime("%B %d, %Y"),
            "author":  document.project.owner.username if document.project.owner else "—",
            "version": f"1.{new_count}",
        }

        #  Start regenerate: set generation to loading (Bar 2)
        gen_doc.status = "IN_PROGRESS"
        gen_doc.save(update_fields=["status"])

        try:
            if document.doc_type == "BRD":
                text, path, meta = generate_brd_from_schema(
                    gen_doc.extraction.filled_schema,
                    document_id   = document.id,
                    project_name  = document.project.name or "",
                    output_subdir = "pending",
                    cover_meta    = cover_meta,
                )
            else:
                text, path, meta = generate_mom_from_schema(
                    gen_doc.extraction.filled_schema,
                    document_id   = document.id,
                    project_name  = document.project.name or "",
                    output_subdir = "pending",
                    cover_meta    = cover_meta,
                )
        except GenerationError as e:
            gen_doc.status = "FAILED"
            gen_doc.meta   = {"error": str(e), "regenerate_count": count}
            gen_doc.save(update_fields=["status", "meta"])
            return Response({"error": str(e)}, status=400)

        remaining             = MAX_REGENERATE_ATTEMPTS - new_count
        meta["regenerate_count"] = new_count

        gen_doc.content           = text
        gen_doc.pending_file.name = path
        gen_doc.status            = "GENERATED"
        gen_doc.is_approved       = False
        gen_doc.meta              = meta
        gen_doc.save(update_fields=["content", "pending_file", "status", "is_approved", "meta"])

        return Response({
            "document_id":          document.id,
            "status":               gen_doc.status,
            "pending_url":          gen_doc.pending_file.url,
            "regenerate_count":     new_count,
            "regenerate_remaining": remaining,
            "final_attempt":        remaining == 0,
            "message": "Last attempt." if remaining == 0 else f"{remaining} attempt(s) remaining.",
        })


class ApproveDocumentAPIView(APIView):
    """
    المستخدم يضغط Approve →
    ينقل الملف من media/pending/ إلى media/documents/ بشكل دائم.
    """
    permission_classes = [AllowAny]

    def post(self, request, document_id):
        try:
            gen_doc = GeneratedDocument.objects.get(document_id=document_id)
        except GeneratedDocument.DoesNotExist:
            return Response({"error": "No generated document found."}, status=400)

        document = gen_doc.document

        if gen_doc.status != "GENERATED":
            return Response({"error": "Must be GENERATED to approve."}, status=400)

        if not gen_doc.pending_file:
            return Response({"error": "No pending file."}, status=400)

        # ننقل الملف من pending إلى documents بشكل دائم
        final_name = f"{document.doc_type.lower()}_{document.id}.docx"
        with gen_doc.pending_file.open("rb") as f:
            gen_doc.generated_file.save(final_name, File(f), save=False)

        gen_doc.pending_file.delete(save=False)
        gen_doc.pending_file = None
        gen_doc.status       = "APPROVED"
        gen_doc.is_approved  = True
        gen_doc.save(update_fields=["generated_file", "pending_file", "status", "is_approved"])

        return Response({
            "document_id":  document.id,
            "status":       gen_doc.status,
            "download_url": gen_doc.generated_file.url,
            "message":      "Document approved and saved.",
        })