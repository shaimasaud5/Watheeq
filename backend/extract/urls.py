from django.urls import path
from .views import ExtractAPIView, extract_mom
from .dynamic_views import DynamicExtractAPIView
from .template_convert_views import TemplateConvertAPIView
from .processing_views import ProcessingAPIView

urlpatterns = [
   path("extract/",ExtractAPIView.as_view(),name="extract"),
   path("extract-mom/", extract_mom, name="extract-mom"),
   path("extract-dynamic/", DynamicExtractAPIView.as_view()),
   path("convert-template/", TemplateConvertAPIView.as_view()),
   path("process-document/", ProcessingAPIView.as_view()),
   ]