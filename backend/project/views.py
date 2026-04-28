from django.shortcuts import render

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.decorators import login_required

from .models import Project, Meeting, Document
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import CreateProjectSerializer
from django.shortcuts import get_object_or_404


@csrf_exempt
def create_project_meeting_brd(request):
    
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    data = json.loads(request.body.decode("utf-8"))

    doc_type = data.get("document_type", "BRD").upper()
    supported_types = ["BRD", "MOM"]
    if doc_type not in supported_types:
        return JsonResponse(
            {"error": f"Supported document types: {', '.join(supported_types)}"},
            status=400
        )

    with transaction.atomic():
        project = Project.objects.create(
            name=data.get("project_name", "").strip()
        )

        meeting = Meeting.objects.create(
            project=project,
            title=data.get("meeting_title", "").strip(),
        )

        document = Document.objects.create(
            project=project,
            doc_type=doc_type,
            content=""
        )

    return JsonResponse({
        "project_id":  project.id,
        "meeting_id":  meeting.id,
        "document_id": document.id,
        "doc_type":    document.doc_type,
    }, status=201)


class CreateProjectAPI(APIView):
    """
    POST /api/project/create/

    Creates a Project, Meeting, Document, and Transcript in one atomic operation.
    Returns document_id which must be passed to task 3 (extract task) so it can
    call POST /api/generation/documents/{document_id}/set-schema/ when done.

    Supported document_type values: BRD, MOM
    """
    def post(self, request):
        serializer = CreateProjectSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=201)