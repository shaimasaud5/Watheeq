from django.urls import path
from .views import CreateProjectAPI, MeetingStatusAPI, PipelineStatusAPI

urlpatterns = [
    # Create new project + meeting + document and trigger Recall bot
    path("projects/create/", CreateProjectAPI.as_view()),

    # Return current meeting status (used for frontend progress bar polling - Bar 1)
    # Agent launch → Agent joins meeting → Meeting ends → Transcript generated
    path("meetings/<int:meeting_id>/status/", MeetingStatusAPI.as_view()),

    # Return pipeline stages status (used for frontend progress bar polling - Bar 2)
    # Cleaning → Chunking & Translation → Extraction → Generation
    path("meetings/<int:meeting_id>/pipeline-status/", PipelineStatusAPI.as_view()),
]