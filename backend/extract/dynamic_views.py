import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import BRDExtraction,MOMExtraction
from .dynamic_prompts import build_dynamic_prompt
from .llm_service import safe_json_loads
import requests
from .template_loader import load_template_from_json_file 
import os 

def fill_not_mentioned(data):
    if isinstance(data, dict):
        return {
            k: fill_not_mentioned(v) if v not in ["", None, []] else "NOT MENTION"
            for k, v in data.items()
        }

    elif isinstance(data, list):
        if not data:
            return "NOT MENTION"
        return [fill_not_mentioned(item) for item in data]

    return data
class DynamicExtractAPIView(APIView):
    permission_classes = [AllowAny]

    OLLAMA_URL = "http://ollama:11434/api/generate"
    MODEL_NAME = "llama3.2"

    def post(self, request, *args, **kwargs):
      doc_type = request.data.get("doc_type", "GENERIC")
      doc_type = str(doc_type).upper().strip()

      transcript = request.data.get("transcript")
      template_text = request.data.get("template_text")
      schema = request.data.get("schema")

      print("DOC TYPE:", doc_type)
      print("TRANSCRIPT RAW:", transcript)
      print("SCHEMA RAW:", schema)
      

      if not doc_type or not isinstance(doc_type, str):
         return Response(
            {"error": "Please provide 'doc_type' as a string."},
            status=status.HTTP_400_BAD_REQUEST,
         )
      doc_type = doc_type.strip().upper()

      if template_text and isinstance(template_text, str) and template_text.strip():
         structure_source = "template_text"
         template_text = template_text.strip()
      else:
         structure_source = "default_schema"

      if not transcript or not isinstance(transcript, str):
         return Response(
               {"error": "Please provide 'transcript' as a string."},
               status=status.HTTP_400_BAD_REQUEST,
         )
      
      if structure_source == "default_schema":
         if doc_type == "BRD":
            schema_path = os.path.join(os.path.dirname(__file__), "schema.json")
         elif doc_type == "MOM":
            schema_path = os.path.join(os.path.dirname(__file__), "mom_schema.json")
         else:
            return Response(
                  {"error": f"Unsupported doc_type: {doc_type}"},
                  status=status.HTTP_400_BAD_REQUEST,
            )

         schema = load_template_from_json_file(schema_path)
      elif structure_source == "template_text":
          template = template_text
      
      if structure_source == "default_schema":
         template = self._empty_from_schema(schema)

      if structure_source == "default_schema":
          extracted=json.loads(json.dumps(template))
      else:
          extracted={}

      llm_result = self._extract_with_llm(transcript, template,doc_type)
      if isinstance(llm_result, dict):
         extracted = fill_not_mentioned(llm_result)

      if isinstance(llm_result, dict):
         extracted = self._merge_into_template(extracted, llm_result)

      if doc_type == "BRD":
         obj=BRDExtraction.objects.create(
            transcript=transcript,
            extracted_data=extracted
         )
      elif doc_type == "MOM":
         obj=MOMExtraction.objects.create(
            transcript=transcript,
            extracted_data=extracted
         )
      else:
          return Response(
              {"error":f"unsupported doc_type"},
              status = status.HTTP_400_BAD_REQUEST,
          )
      extracted = fill_not_mentioned(extracted)
      return Response(
         {
               "status": "ok",
               "id":obj.id,
               "schema_type": doc_type ,
               "received_chars": len(transcript),
               "preview": transcript[:120],
               "extracted": extracted,
         },
         status=status.HTTP_200_OK,
      )

    def _empty_from_schema(self, schema: dict):
        t = schema.get("type")

        if t == "object":
            props = schema.get("properties", {}) or {}
            return {k: self._empty_from_schema(v) for k, v in props.items()}

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

    def _extract_with_llm(self, transcript: str, template, doc_type: str):
      prompt = None

      #  الحالة 1: schema جاهزة (dict)
      if isinstance(template, dict):
         if doc_type == "BRD":
               from .prompts import build_brd_prompt
               prompt = build_brd_prompt(template, transcript)

         elif doc_type == "MOM":
               from .mom_prompts import build_mom_extraction_prompt
               import json
               schema_text = json.dumps(template, ensure_ascii=False)
               prompt = build_mom_extraction_prompt(transcript, schema_text)

      #  الحالة 2: template_text (نص من pdf/docx)
      else:
         from .dynamic_prompts import build_dynamic_prompt
         prompt = build_dynamic_prompt(template, transcript, doc_type)

      #  حماية
      if not prompt:
         raise ValueError(f"Failed to build prompt for doc_type: {doc_type}")

      payload = {
         "model": self.MODEL_NAME,
         "prompt": prompt,
         "stream": False,
         "format": "json",
         "options": {"temperature": 0},
      }

      try:
         resp = requests.post(self.OLLAMA_URL, json=payload, timeout=350)
         resp.raise_for_status()
         raw = resp.json().get("response", "")
         print("DYNAMIC RAW RESPONSE:", raw[:1000])
      except Exception as e:
         print("DYNAMIC OLLAMA ERROR:", str(e))
         return None

      parsed = safe_json_loads(raw)
      return parsed if isinstance(parsed, dict) else None