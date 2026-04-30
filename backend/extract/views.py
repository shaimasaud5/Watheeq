# extract/views.py
# ─────────────────
# endpoint احتياطي فقط — الاستخراج الفعلي يشتغل تلقائياً
# من processing/pipeline.py بعد اكتمال مهمة 2.
# هذا الـ endpoint مفيد للاختبار اليدوي من Django admin أو Postman.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from project.models import Document
from processing.models import TranscriptChunk
from .models import Extraction
from .extractor import extract_brd, extract_mom


class ExtractAPIView(APIView):
    """
    POST /api/extract/
    Body: { "document_id": 1 }

    للاختبار اليدوي فقط.
    في الإنتاج يُستدعى تلقائياً من processing/pipeline.py
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        document_id = request.data.get("document_id")
        if not document_id:
            return Response({"error": "document_id is required."}, status=400)

        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({"error": f"Document {document_id} not found."}, status=404)

        # نوصل للـ transcript عبر: document → project → meeting → transcript
        try:
            transcript = document.project.meeting.transcript
        except Exception:
            return Response({"error": "No transcript found for this project."}, status=400)

        # نسحب الـ chunks المكتملة من مهمة 2
        chunks = list(
            TranscriptChunk.objects.filter(
                transcript=transcript,
                status="completed",
            ).order_by("chunk_index").values("semantic_english_text", "embedding")
        )

        if not chunks:
            return Response({"error": "No completed chunks found. Task 2 may not have finished."}, status=400)

        print(f"\n[ EXTRACT ] Starting {document.doc_type} extraction for document {document_id}")
        print(f"[ EXTRACT ] Using {len(chunks)} chunks")

        if document.doc_type == "BRD":
            filled_schema = extract_brd(chunks)
        elif document.doc_type == "MOM":
            filled_schema = extract_mom(chunks)
        else:
            return Response({"error": f"Unsupported doc_type: {document.doc_type}"}, status=400)

        Extraction.objects.update_or_create(
            document=document,
            defaults={
                "filled_schema": filled_schema,
                "chunk": TranscriptChunk.objects.filter(
                    transcript=transcript, status="completed"
                ).first(),
            }
        )

        return Response({
            "status":      "ok",
            "document_id": document_id,
            "doc_type":    document.doc_type,
            "message":     "Extraction complete.",
        })
