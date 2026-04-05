from django.urls import path, include
from .views import CreateProjectAPI

urlpatterns = [
    path("projects/create/", CreateProjectAPI.as_view()),
    path("api/", include("extract.urls")),
]