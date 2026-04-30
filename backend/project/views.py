from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .serializers import CreateProjectSerializer
from .services import request_recall_bot


class CreateProjectAPI(APIView):
    """
    Handles the New Project & Meeting Setup form submission.
    When the user clicks 'Generate Document', this view:
    1. Validates and saves Project, Meeting, and Document in the database
    2. Sends the meeting link to Recall.ai so the bot joins the meeting
    """

    # Temporarily disabled for testing — re-enable after frontend is ready
    permission_classes = [AllowAny]

    def post(self, request):
        """
        POST /api/projects/create/
        Expects: project info + meeting setup fields from the form
        Returns: project_id, meeting_id, document_id, doc_type
        """

        # 1. Pass incoming data to the serializer for validation
        #    If validation fails, an error response is returned automatically
        serializer = CreateProjectSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # 2. Save validated data → creates Project, Meeting, Document in DB
        result = serializer.save()

        # 3. Send the meeting link to Recall.ai so the bot joins the meeting
        #    The bot will listen silently and return the transcript when done
        request_recall_bot(
            meeting_id=result["meeting_id"],
        )

        # 4. Return the created IDs to the frontend
        return Response(result, status=201)