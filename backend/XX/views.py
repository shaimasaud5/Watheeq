from rest_framework.response import Response
from rest_framework.decorators import api_view
from .llama_client import ask_llama

@api_view(["GET"])
def test_api(request):
    return Response({"message": "DRF is working"})

@api_view(["GET"])
def llama_test(request):
    out = ask_llama("Hi", max_tokens=10)
    return Response({"llama": out})
