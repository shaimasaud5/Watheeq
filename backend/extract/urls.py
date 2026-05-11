from django.urls import path
from .views import ExtractAPIView

urlpatterns = [
    # For manual testing only
    path("extract/", ExtractAPIView.as_view(), name="extract"),
]
