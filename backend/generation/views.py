# generation/views.py
from django.core.files.base import File
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GeneratedDocument
from .services.orchestrator import GenerationError, generate_brd_from_schema, generate_mom_from_schema

MAX_REGENERATE_ATTEMPTS = 3


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