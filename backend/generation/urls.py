from django.urls import path
from .views import RegenerateDocumentAPIView, ApproveDocumentAPIView

urlpatterns = [
    path("documents/<int:document_id>/regenerate/", RegenerateDocumentAPIView.as_view()),
    path("documents/<int:document_id>/approve/",    ApproveDocumentAPIView.as_view()),
]