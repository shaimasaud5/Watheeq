from pathlib import Path
import json
import os
import requests as http_requests

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view , permission_classes

from .models import BRDExtraction , MOMExtraction
from .post_processing import post_process_extracted
from .llm_service import extract_brd_with_llm, extract_mom_with_llm
from .mom_post_processing import post_process_mom
from .mom_prompts import build_mom_extraction_prompt

class ExtractAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        transcript = request.data.get("transcript")
        if not transcript or not isinstance(transcript, str):
            return Response(
                {"error": "Please provide 'transcript' as a string."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        schema = self._load_schema()
        if isinstance(schema, Response):
            return schema

        template = self._empty_from_schema(schema)
        extracted = json.loads(json.dumps(template))

        llm_result = extract_brd_with_llm(template, transcript)
        if isinstance(llm_result, dict):
            extracted = self._merge_into_template(extracted, llm_result)

        extracted = post_process_extracted(extracted, transcript)

        BRDExtraction.objects.create(
            transcript=transcript,
            # extracted_data
            filled_schema=extracted
        )
        doc_id = request.data.get("document_id")
        if doc_id:
            http_requests.post(
                f"http://localhost:8000/api/generation/documents/{doc_id}/set-schema/",
                json={"filled_schema": extracted},
            )

        return Response(
            {
                "status": "ok",
                "received_chars": len(transcript),
                "preview": transcript[:120],
                "extracted": extracted,
            },
            status=status.HTTP_200_OK,
        )

    def _load_schema(self):
        schema_path = Path(__file__).parent / "schema.json"
        if not schema_path.exists():
            return Response(
                {"error": "schema.json not found in extract app folder."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            return json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as e:
            return Response(
                {"error": f"Failed to read schema.json: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _empty_from_schema(self, schema: dict):
        t = schema.get("type")
        if t == "object":
            props = schema.get("properties", {}) or {}
            out = {}
            for k, subschema in props.items():
                out[k] = self._empty_from_schema(subschema)
            return out
        if t == "array":
            return []
        return None

    def _merge_into_template(self, template, llm_data):
        if isinstance(template, dict):
            if not isinstance(llm_data, dict):
                return template
            for k in template.keys():
                if k in llm_data:
                    template[k] = self._merge_into_template(template[k], llm_data[k])
            return template

        if isinstance(template, list):
            return llm_data if isinstance(llm_data, list) else template

        return llm_data if llm_data is not None else template
    
    #MOM ---------------------------------




@api_view(["POST"])
@permission_classes([AllowAny])
def extract_mom(request):
    transcript = request.data.get("transcript", "")

    if not transcript:
        return Response(
            {"status": "error", "message": "Transcript is required"},
            status=400
        )

    try:
        result = extract_mom_with_llm(transcript)
        MOMExtraction.objects.create(
            transcript=transcript,
            # extracted_data
            filled_schema=result
        )
        doc_id = request.data.get("document_id")
        if doc_id:
            http_requests.post(
                 f"http://localhost:8000/api/generation/documents/{doc_id}/set-schema/",
                 json={"filled_schema": result},
             )

        return Response({
            "status": "ok",
            "extracted": result
        })

    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=500
        )