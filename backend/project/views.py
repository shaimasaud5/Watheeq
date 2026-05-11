from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Meeting
from .serializers import CreateProjectSerializer
from .services import request_recall_bot
from generation.models import GeneratedDocument
from project.models import Project


class CreateProjectAPI(APIView):
    """
    Handles the New Project & Meeting Setup form submission.
    When the user clicks 'Generate Document', this view:
    1. Validates and saves Project, Meeting, and Document in the database
    2. Sends the meeting link to Recall.ai so the bot joins the meeting
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CreateProjectSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        request_recall_bot(
            meeting_id=result["meeting_id"],
        )

        return Response(result, status=201)


class MeetingStatusAPI(APIView):
    """
    Returns the current meeting lifecycle status.
    Used by the frontend polling to update the first progress bar.
    """

    permission_classes = [AllowAny]

    def get(self, request, meeting_id):
        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found"}, status=404)

        return Response({
            "meeting_id": meeting.id,
            "status": meeting.status,
        })
    

class PipelineStatusAPI(APIView):
    """
    Returns the status of each internal pipeline stage.
    Used by the frontend polling to update the second progress bar.
    """

    permission_classes = [AllowAny]

    def get(self, request, meeting_id):
        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response({"error": "Meeting not found"}, status=404)

        transcript = getattr(meeting, "transcript", None)

        preprocessing_status = transcript.status if transcript else "pending"

        processing_status = "pending"
        if transcript and hasattr(transcript, "processing_result"):
            processing_status = transcript.processing_result.status

        extraction_status = "pending"
        generation_status = "DRAFT"

        documents = meeting.project.documents.all()

        for document in documents:
            if hasattr(document, "extraction"):
                extraction_status = document.extraction.status

            if hasattr(document, "generated"):
                generation_status = document.generated.status

        return Response({
            "meeting_id": meeting.id,
            "preprocessing": preprocessing_status,
            "processing": processing_status,
            "extraction": extraction_status,
            "generation": generation_status,
        })


def home_view(request):
    user = request.user
    
    total_projects = Project.objects.filter(user=user).count()
    
    pending_approval = GeneratedDocument.objects.filter(
        document__project__user=user,
        status='GENERATED'
    ).count()
    
    total_approved = GeneratedDocument.objects.filter(
        document__project__user=user,
        status='APPROVED'
    ).count()
    
    context = {
        'total_projects': total_projects,
        'pending_approval': pending_approval,
        'total_approved': total_approved,
    }
    return render(request, 'frontend/home.html', context)

    

class DeleteProjectAPI(APIView):
    """
    Deletes a project and all related data (meeting, transcript, documents, etc.)
    Only the project owner can delete it.
    """

    permission_classes = [AllowAny]

    def delete(self, request, project_id):
        from .models import Project

        try:
            project = Project.objects.get(id=project_id, owner=request.user)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=404)

        project.delete()
        return Response({"message": "Project deleted successfully"}, status=200)