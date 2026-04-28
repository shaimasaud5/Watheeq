# generation/urls.py
from django.urls import path
from .views import (
    SetSchemaAPIView,
    GenerateDocumentAPIView,
    RegenerateDocumentAPIView,
    ApproveDocumentAPIView,
)

urlpatterns = [
    # Called by task 3 after extraction
    path("documents/<int:document_id>/set-schema/",
         SetSchemaAPIView.as_view(),
         name="set-schema"),

    # First-time generation → pending_file
    path("documents/<int:document_id>/generate/",
         GenerateDocumentAPIView.as_view(),
         name="generate-document"),

    # User clicks Regenerate → new pending_file
    path("documents/<int:document_id>/regenerate/",
         RegenerateDocumentAPIView.as_view(),
         name="regenerate-document"),

    # User clicks Approve → pending_file → generated_file
    path("documents/<int:document_id>/approve/",
         ApproveDocumentAPIView.as_view(),
         name="approve-document"),
]