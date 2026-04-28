from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

class TemplateConvertAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    @extend_schema(
      request={
         'multipart/form-data': {
               'type': 'object',
               'properties': {
                  'file': {
                     'type': 'string',
                     'format': 'binary'
                  },
               },
               'required': ['file'],
         }
      },
      responses={200: dict},
   )
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        try:
            from .file_text_extractor import extract_text_from_template
            template_text = extract_text_from_template(file)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        return Response({
            "status": "ok",
            "template_text": template_text
        })