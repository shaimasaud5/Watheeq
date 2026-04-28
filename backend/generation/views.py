# generation/views.py
# -------------------
# Endpoints:
#   POST /api/generation/documents/{id}/set-schema/
#   POST /api/generation/documents/{id}/generate/
#   POST /api/generation/documents/{id}/regenerate/
#   POST /api/generation/documents/{id}/approve/
#
# File flow:
#   generate/regenerate -> pending_file
#   approve             -> generated_file
#
# REGENERATE LIMIT:
#   The user may call regenerate/ at most MAX_REGENERATE_ATTEMPTS times.
#   The counter is stored in doc.meta["regenerate_count"].
#   On the final allowed attempt the response includes "final_attempt": true
#   so the frontend can hide the Regenerate button and show a warning.
#   After that, regenerate/ returns HTTP 400 with "error": "limit_reached".

from django.core.files.base import File
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from project.models import Document

from .services.orchestrator import (
    GenerationError,
    generate_brd_from_schema,
    generate_mom_from_schema,
)

SUPPORTED_TYPES = ["BRD", "MOM"]

# Maximum number of times the user may press "Regenerate".
# First generation (generate/) does NOT count toward this limit.
MAX_REGENERATE_ATTEMPTS = 3


def _get_project_name(doc):
    try:
        return doc.project.name or "" if doc.project else ""
    except Exception:
        return ""


def _run_generation(doc):
    project_name = _get_project_name(doc)
    if doc.doc_type == "BRD":
        return generate_brd_from_schema(
            doc.extracted_json,
            document_id=doc.id,
            project_name=project_name,
            output_subdir="pending",
        )
    if doc.doc_type == "MOM":
        return generate_mom_from_schema(
            doc.extracted_json,
            document_id=doc.id,
            project_name=project_name,
            output_subdir="pending",
        )
    raise GenerationError(f"Unsupported doc_type: {doc.doc_type}")


def _delete_pending_file(doc):
    if doc.pending_file:
        try:
            storage = doc.pending_file.storage
            if doc.pending_file.name and storage.exists(doc.pending_file.name):
                storage.delete(doc.pending_file.name)
        except Exception:
            pass
        doc.pending_file = None


def _delete_generated_file(doc):
    if doc.generated_file:
        try:
            storage = doc.generated_file.storage
            if doc.generated_file.name and storage.exists(doc.generated_file.name):
                storage.delete(doc.generated_file.name)
        except Exception:
            pass
        doc.generated_file = None


def _get_regenerate_count(doc) -> int:
    """Returns the current regenerate attempt count stored in doc.meta."""
    try:
        return int((doc.meta or {}).get("regenerate_count", 0))
    except (TypeError, ValueError):
        return 0


def _increment_regenerate_count(meta: dict) -> dict:
    """Returns a copy of meta with regenerate_count incremented by 1."""
    updated = dict(meta or {})
    updated["regenerate_count"] = int(updated.get("regenerate_count", 0)) + 1
    return updated


class SetSchemaAPIView(APIView):
    """
    POST /api/generation/documents/{id}/set-schema/
    Called by task 3. Saves filled_schema, sets status=EXTRACTED.
    Body: { "filled_schema": {...} }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)
        filled_schema = request.data.get("filled_schema")

        if not filled_schema:
            return Response(
                {"error": "filled_schema is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(filled_schema, dict):
            return Response(
                {"error": "filled_schema must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc.extracted_json = filled_schema
        doc.status = "EXTRACTED"
        doc.save(update_fields=["extracted_json", "status"])

        return Response(
            {
                "document_id": doc.id,
                "doc_type": doc.doc_type,
                "status": doc.status,
                "message": "Schema saved. Ready for generation.",
            }
        )


class GenerateDocumentAPIView(APIView):
    """
    POST /api/generation/documents/{id}/generate/
    First-time generation. Result goes to pending_file.
    User must call approve/ to make it permanent.
    EXTRACTED -> GENERATED

    NOTE: This endpoint does NOT count toward the regenerate limit.
    The regenerate_count in meta is reset to 0 on first generate.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)

        if doc.doc_type not in SUPPORTED_TYPES:
            return Response(
                {"error": f"Supported types: {', '.join(SUPPORTED_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not doc.extracted_json:
            return Response(
                {"error": "No extracted_json. Call set-schema/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if doc.status == "DRAFT":
            doc.status = "EXTRACTED"
            doc.save(update_fields=["status"])

        try:
            generated_text, rel_file_path, meta = _run_generation(doc)
        except GenerationError as e:
            doc.status = "FAILED"
            doc.meta = {"error": str(e)}
            doc.save(update_fields=["status", "meta"])
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Reset regenerate counter on fresh generation
        meta["regenerate_count"] = 0

        _delete_pending_file(doc)
        doc.content = generated_text
        doc.pending_file.name = rel_file_path
        doc.status = "GENERATED"
        doc.is_approved = False
        doc.meta = meta
        doc.save(update_fields=["content", "pending_file", "status", "is_approved", "meta"])

        return Response(
            {
                "document_id": doc.id,
                "doc_type": doc.doc_type,
                "project": _get_project_name(doc),
                "status": doc.status,
                "pending_url": doc.pending_file.url if doc.pending_file else None,
                "regenerate_count": 0,
                "regenerate_remaining": MAX_REGENERATE_ATTEMPTS,
                "preview": (generated_text[:1500] + "...") if len(generated_text) > 1500 else generated_text,
                "meta": meta,
                "message": "Document generated. Waiting for approval.",
            }
        )


class RegenerateDocumentAPIView(APIView):
    """
    POST /api/generation/documents/{id}/regenerate/
    Re-runs generation from same extracted_json. No new extraction.
    GENERATED/APPROVED/FAILED -> GENERATED

    LIMIT: MAX_REGENERATE_ATTEMPTS (3) total regenerations allowed.

    Response includes:
      "regenerate_count"     — how many times regenerate/ has been called so far
      "regenerate_remaining" — how many more times it can be called (0 = last was just used)
      "final_attempt"        — true if this was the last allowed regeneration
                               → frontend should hide the Regenerate button

    When the limit is reached, returns HTTP 400:
      { "error": "limit_reached",
        "message": "...",
        "regenerate_count": 3 }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)

        if not doc.extracted_json:
            return Response(
                {"error": "No extracted_json. Cannot regenerate."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if doc.status not in ("GENERATED", "APPROVED", "FAILED"):
            return Response(
                {"error": f"Cannot regenerate from status: {doc.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_count = _get_regenerate_count(doc)

        # Hard limit: user has already used all attempts
        if current_count >= MAX_REGENERATE_ATTEMPTS:
            return Response(
                {
                    "error": "limit_reached",
                    "message": (
                        f"You have used all {MAX_REGENERATE_ATTEMPTS} regeneration attempts. "
                        "Please approve the current version."
                    ),
                    "regenerate_count": current_count,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generated_text, rel_file_path, meta = _run_generation(doc)
        except GenerationError as e:
            doc.status = "FAILED"
            doc.meta = {"error": str(e), "regenerate_count": current_count}
            doc.save(update_fields=["status", "meta"])
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Increment the counter in meta
        new_count = current_count + 1
        meta["regenerate_count"] = new_count
        remaining = MAX_REGENERATE_ATTEMPTS - new_count
        is_final = remaining == 0

        _delete_pending_file(doc)
        doc.content = generated_text
        doc.pending_file.name = rel_file_path
        doc.status = "GENERATED"
        doc.is_approved = False
        doc.meta = meta
        doc.save(update_fields=["content", "pending_file", "status", "is_approved", "meta"])

        message = (
            "This was your last regeneration. Please review and approve the document."
            if is_final
            else f"Document regenerated. {remaining} regeneration(s) remaining."
        )

        return Response(
            {
                "document_id": doc.id,
                "doc_type": doc.doc_type,
                "project": _get_project_name(doc),
                "status": doc.status,
                "pending_url": doc.pending_file.url if doc.pending_file else None,
                "regenerate_count": new_count,
                "regenerate_remaining": remaining,
                "final_attempt": is_final,
                "preview": (generated_text[:1500] + "...") if len(generated_text) > 1500 else generated_text,
                "meta": meta,
                "message": message,
            }
        )


class ApproveDocumentAPIView(APIView):
    """
    POST /api/generation/documents/{id}/approve/
    User approves the document.
    pending_file -> generated_file
    GENERATED -> APPROVED
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)

        if doc.status != "GENERATED":
            return Response(
                {"error": f"Must be GENERATED to approve. Current: {doc.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not doc.pending_file:
            return Response(
                {"error": "No pending file. Run generate/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _delete_generated_file(doc)

        # Copy the reviewed file into generated_file's upload_to=documents/.
        final_name = f"{doc.doc_type.lower()}_{doc.id}.docx"
        with doc.pending_file.open("rb") as pending_stream:
            doc.generated_file.save(final_name, File(pending_stream), save=False)

        _delete_pending_file(doc)
        doc.status = "APPROVED"
        doc.is_approved = True
        doc.save(update_fields=["generated_file", "pending_file", "status", "is_approved"])

        return Response(
            {
                "document_id": doc.id,
                "doc_type": doc.doc_type,
                "project": _get_project_name(doc),
                "status": doc.status,
                "is_approved": doc.is_approved,
                "download_url": doc.generated_file.url if doc.generated_file else None,
                "message": "Document approved and saved to Documents.",
            }
        )