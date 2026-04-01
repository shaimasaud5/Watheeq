from django.urls import path
from .views import ExtractAPIView, extract_mom

urlpatterns = [
   path("extract/",ExtractAPIView.as_view(),name="extract"),
   path("extract-mom/", extract_mom, name="extract-mom"),]