# extract/extractor.py
# ─────────────────────
# المنطق الأساسي للاستخراج (RAG).
#
# لكل فقرة في السكيما:
# 1. نولّد embedding لاسم الفقرة بنفس نموذج مهمة 2 (mxbai-embed-large)
# 2. نقارنه بكل chunk embeddings المحفوظة من مهمة 2
# 3. نأخذ أقرب 3 chunks
# 4. نرسل للـ LLM: "استخرج قيمة هذي الفقرة من هذي النصوص"
# 5. نجمع كل الفقرات في filled_schema كامل

import copy
from .embedding_service import generate_embedding
from .retrieval_service  import retrieve_top_chunks
from .llm_service        import extract_section
from .schemas            import BRD_SCHEMA, MOM_SCHEMA


def _merge(template, extracted):
    """
    يدمج النتيجة من LLM في الـ template.
    يحافظ على هيكل الـ template إذا رجع LLM شيء خاطئ.
    """
    if isinstance(template, dict):
        if not isinstance(extracted, dict):
            return template
        result = copy.deepcopy(template)
        for key in template:
            if key in extracted:
                result[key] = _merge(template[key], extracted[key])
        return result
    if isinstance(template, list):
        return extracted if isinstance(extracted, list) else template
    return extracted if extracted is not None else template


def _extract(schema: dict, chunks: list, doc_type: str) -> dict:
    """
    الدالة الأساسية — تعمل لكلا BRD و MOM.

    chunks: قائمة من {"semantic_english_text": str, "embedding": list}
            مسحوبة من TranscriptChunk في مهمة 2
    """
    filled = copy.deepcopy(schema)

    for section_name, section_template in schema.items():
        print(f"  [ {doc_type} ] Extracting: {section_name}...")

        # 1. نولّد embedding لاسم الفقرة
        section_embedding = generate_embedding(section_name)

        # 2. نجيب أقرب 3 chunks لهذي الفقرة
        top_chunks = retrieve_top_chunks(
            section_embedding=section_embedding,
            chunks=chunks,
            top_k=3,
        )

        # 3. ندمج النصوص في context واحد للـ LLM
        context = "\n\n---\n\n".join(top_chunks)

        # 4. نرسل للـ LLM ونملأ الفقرة
        result = extract_section(section_name, section_template, context, doc_type)

        # 5. ندمج النتيجة — إذا فشل LLM نحتفظ بالـ template الفارغ
        if result and section_name in result:
            filled[section_name] = _merge(section_template, result[section_name])

    return filled


def extract_brd(chunks: list) -> dict:
    """يستخرج filled_schema لوثيقة BRD."""
    return _extract(BRD_SCHEMA, chunks, "BRD")


def extract_mom(chunks: list) -> dict:
    """يستخرج filled_schema لوثيقة MOM."""
    return _extract(MOM_SCHEMA, chunks, "MOM")
