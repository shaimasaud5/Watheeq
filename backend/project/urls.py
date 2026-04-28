from django.urls import path
from .views import CreateProjectAPI

urlpatterns = [
    # Endpoint to create a new project, meeting, and document
    # Called when the user clicks 'Generate Document' in the form
    # POST /api/projects/create/
    path("projects/create/", CreateProjectAPI.as_view()),
]