from django.urls import path
from .views import ExtractAPIView

urlpatterns = [
    # للاختبار اليدوي فقط
    path("extract/", ExtractAPIView.as_view(), name="extract"),
]
