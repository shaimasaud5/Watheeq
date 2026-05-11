from django.urls import path
from .views import RegenerateDocumentAPIView, ApproveDocumentAPIView, GenerateNewDocumentAfterProjectAPIView, DeleteDocumentAPIView

urlpatterns = [
    path("documents/<int:document_id>/regenerate/", RegenerateDocumentAPIView.as_view()),
    path("documents/<int:document_id>/approve/",    ApproveDocumentAPIView.as_view()),
    path("projects/<int:project_id>/generate-new-document/", GenerateNewDocumentAfterProjectAPIView.as_view(), name="generate_new_document_after_project"),
    path("documents/<int:document_id>/delete/",     DeleteDocumentAPIView.as_view()),
]