from django.urls import path
from .views import test_api, llama_test

urlpatterns = [
    path("test/", test_api),
    path("llama-test/", llama_test),
]
