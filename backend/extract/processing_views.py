import requests
from django.apps import apps
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.generics import GenericAPIView

from .serializers import ProcessingRequestSerializer
from .file_text_extractor import extract_text_from_template
from .query_service import get_query_by_doc_type
from .retrieval_service import retrieve_top_chunks
from .embedding_service import generate_embedding


class ProcessingAPIView(GenericAPIView):
    serializer_class = ProcessingRequestSerializer
    permission_classes = [AllowAny]

    DYNAMIC_URL = "http://backend:8000/api/extract-dynamic/"

    def _get_chunk_model(self):
        for model in apps.get_models():
            field_names = {f.name for f in model._meta.fields}
            if {"transcript", "semantic_english_text", "embedding"}.issubset(field_names):
                return model
        return None

    def _get_top_k(self, chunks_count):
        if chunks_count <= 3:
            return 2
        elif chunks_count <= 6:
            return 4
        elif chunks_count <= 10:
            return 7
        elif chunks_count <= 20:
            return 14
        return 20

    def _build_transcript(self, chunks_with_embeddings, doc_type):
        query = get_query_by_doc_type(doc_type)
        query_embedding = generate_embedding(query)

        top_k = self._get_top_k(len(chunks_with_embeddings))
        top_chunks = retrieve_top_chunks(query_embedding, chunks_with_embeddings, top_k=top_k)

        clean_chunks = []
        for chunk in top_chunks:
            if "sample transcript" in chunk.lower():
                continue
            if len(chunk.strip()) < 30:
                continue
            clean_chunks.append(chunk)

        transcript = " ".join(clean_chunks)
        transcript = transcript.replace('"', '')
        transcript = transcript.replace('’', '')
        return transcript.strip()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc_type = serializer.validated_data["doc_type"]
        transcript_id = serializer.validated_data["transcript_id"]
        template_file = serializer.validated_data.get("template_file")

        chunk_model = self._get_chunk_model()
        if chunk_model is None:
            return Response({
                "status": "pending_integration",
                "message": "Chunk + embedding model is not yet integrated into this project.",
                "doc_type": doc_type,
                "transcript_id": transcript_id,
                "has_template": bool(template_file),
            })

        chunks_qs = chunk_model.objects.filter(
            transcript_id=transcript_id
        ).exclude(
            embedding__isnull=True
        ).exclude(
            semantic_english_text=""
        )

        chunks_with_embeddings = []
        for chunk in chunks_qs:
            chunks_with_embeddings.append({
                "semantic_english_text": chunk.semantic_english_text,
                "embedding": chunk.embedding,
            })

        if not chunks_with_embeddings:
            return Response({
                "status": "no_chunks_found",
                "doc_type": doc_type,
                "transcript_id": transcript_id,
                "has_template": bool(template_file),
            })

        transcript = self._build_transcript(chunks_with_embeddings, doc_type)

        template_text = ""
        if template_file:
            template_text = extract_text_from_template(template_file)

        payload = {
            "doc_type": doc_type,
            "transcript": transcript,
            "template_text": template_text,
        }

        response = requests.post(self.DYNAMIC_URL, json=payload, timeout=300)
        dynamic_data = response.json()

        return Response({
            "status": "ok",
            "doc_type": doc_type,
            "transcript_id": transcript_id,
            "has_template": bool(template_file),
            "retrieved_chunks_count": len(chunks_with_embeddings),
            "final_transcript": transcript,
            "dynamic_status_code": response.status_code,
            "dynamic_response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
        }, status=response.status_code)