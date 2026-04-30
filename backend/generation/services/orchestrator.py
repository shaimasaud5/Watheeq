# generation/services/orchestrator.py
# ─────────────────────────────────────
# "دماغ" عملية التوليد — يربط كل شيء:
# السكيما المستخرجة → LLM → renderer → ملف .docx
#
# دالتان رئيسيتان تُستدعيان من signals.py:
#   generate_brd_from_schema() — لوثيقة BRD
#   generate_mom_from_schema() — لوثيقة MOM
#
# كلتاهما تستدعيان _run_generation() داخلياً

import os
import time
from typing import Any, Dict, Tuple

from django.conf import settings
from docx import Document

from .prompting import (
    build_field_prompt,
    key_to_label,
    value_to_raw_text,
    should_skip_llm,
    is_structural,
)
from .llm_client import generate_text
from .docx_renderer import build_doc_from_json


class GenerationError(Exception):
    pass


_PREAMBLE_STARTS = (
    "here is", "here's", "sure,", "sure!", "certainly,", "of course",
    "this section", "below is", "the following", "as requested",
    "based on", "i will", "i'll", "please find", "in this section",
    "this document", "the document", "note:", "note that", "as a senior",
)


def _clean_llm_output(text: str) -> str:
    """
    ينظف رد الـ LLM:
    - يحذف أسطر المقدمة غير المطلوبة
    - يحذف عناوين Markdown (أسطر تبدأ بـ #)
    - يحذف أسطر الفواصل (--- أو ===)
    - يجمع الأسطر في فقرة واحدة نظيفة
    """
    cleaned = []
    for line in text.strip().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if set(s).issubset(set("-=_ ")):
            continue
        if any(s.lower().startswith(p) for p in _PREAMBLE_STARTS):
            continue
        cleaned.append(s)
    return " ".join(cleaned).strip()


def _dict_has_string_values(d: dict) -> bool:
    """
    يتحقق إذا كان الـ dict يحتوي على قيم نصية.

    مهمة 3 تُرجع بعض الحقول كـ dict يحتوي نصوصاً:
        "executive_summary": {
            "problem": "انخفاض المبيعات",      ← نص → يُرسل للـ LLM
            "expected_benefits": ["فائدة 1"]   ← قائمة → للـ renderer
        }
    """
    return any(isinstance(v, str) and str(v).strip() for v in d.values())


def _run_generation(
    filled_schema: Dict[str, Any],
    document_id: int,
    doc_type: str,
    project_name: str = "",
    output_subdir: str = "pending",
) -> Tuple[str, str, Dict[str, Any]]:
    """
    يشغّل التوليد الفعلي.

    المدخلات:
        filled_schema — السكيما المستخرجة من مهمة 3
        document_id   — رقم الوثيقة لتسمية الملف
        doc_type      — "BRD" أو "MOM"
        project_name  — اسم المشروع يظهر في غلاف الوثيقة
        output_subdir — المجلد داخل media/ لحفظ الملف

    الخطوات:
        1. يمر على كل حقل في السكيما
        2. يقرر حسب شكل القيمة: LLM أم renderer مباشرة
        3. يبني ملف الـ .docx
        4. يرجع النص + مسار الملف + معلومات التوليد
    """
    if not isinstance(filled_schema, dict) or not filled_schema:
        raise GenerationError("filled_schema must be a non-empty JSON object.")

    start = time.time()
    expanded: Dict[str, Any] = {}

    for field_key, field_value in filled_schema.items():

        # تجاهل الحقول الفارغة تماماً
        if field_value in (None, "", [], {}):
            continue

        # ── CASE 1: حقول هيكلية ثابتة ──────────────────────────
        # document_control و meeting_info دائماً تذهب للـ renderer مباشرة
        # لأنها جداول/كتل منظمة لا نريد الـ LLM يحولها لنثر
        if field_key in ("document_control", "meeting_info"):
            expanded[field_key] = ""
            continue

        # ── CASE 2: dict يحتوي نصوصاً ───────────────────────────
        # مثال: "executive_summary": {"problem": "...", "proposed_solution": "..."}
        # كل نص داخله يُرسل للـ LLM بشكل منفصل
        if isinstance(field_value, dict) and _dict_has_string_values(field_value):
            sub_expanded = {}
            for sub_key, sub_val in field_value.items():
                if not sub_val or not isinstance(sub_val, str):
                    continue
                prompt = build_field_prompt(sub_key, sub_val, doc_type=doc_type)
                raw    = generate_text(prompt)
                prose  = _clean_llm_output(raw)
                # fallback: لو الـ LLM رجع نصاً قصيراً جداً أو فارغاً
                if len(prose) < 10:
                    prose = sub_val
                sub_expanded[sub_key] = prose
            expanded[field_key] = sub_expanded
            continue

        # ── CASE 3: قائمة أو dict خالص ─────────────────────────
        # مثال: stakeholders, functional_requirements, risk_analysis
        # تذهب للـ renderer مباشرة كجداول أو نقاط
        if is_structural(field_value):
            expanded[field_key] = ""
            continue

        # ── CASE 4: نص عادي → LLM يكتب نثراً احترافياً ─────────
        prompt = build_field_prompt(field_key, field_value, doc_type=doc_type)
        raw    = generate_text(prompt)
        prose  = _clean_llm_output(raw)
        # fallback: لو الـ LLM رجع نصاً قصيراً جداً أو فارغاً
        # نستخدم البيانات الأصلية من السكيما بدل ترك الحقل فارغاً
        if len(prose) < 10:
            prose = value_to_raw_text(field_value)
        expanded[field_key] = prose

    if not expanded:
        raise GenerationError("LLM returned empty output for every field.")

    elapsed = time.time() - start

    # نص عادي يُحفظ في حقل content في الداتابيس
    generated_text = _build_plain_text(expanded, doc_type)

    # حفظ ملف الـ .docx في media/
    rel_dir = (output_subdir or "pending").strip("/\\") or "pending"
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    # اسم الملف — pending يحتوي timestamp لتجنب التضارب عند الـ regenerate
    if rel_dir == "pending":
        filename = f"{doc_type.lower()}_{document_id}_{int(time.time() * 1000)}.docx"
    else:
        filename = f"{doc_type.lower()}_{document_id}.docx"

    rel_path = f"{rel_dir}/{filename}"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    # نبني الـ .docx ونحفظه
    doc = Document()
    build_doc_from_json(doc, filled_schema, expanded, doc_type, project_name)
    doc.save(abs_path)

    meta = {
        "model":           os.getenv("OLLAMA_MODEL", "llama3"),
        "elapsed_seconds": round(elapsed, 3),
    }

    return generated_text, rel_path, meta


def _build_plain_text(expanded: Dict[str, Any], doc_type: str) -> str:
    """
    يبني نسخة نصية بسيطة من الوثيقة.
    تُحفظ في حقل content في الداتابيس للرجوع إليها.
    """
    title = "Business Requirements Document" if doc_type == "BRD" else "Minutes of Meeting"
    lines = [f"{title}\n"]
    for field_key, prose in expanded.items():
        label = key_to_label(field_key)
        if isinstance(prose, dict):
            lines.append(f"\n{label}")
            for sub_key, sub_prose in prose.items():
                sub_label = key_to_label(sub_key)
                lines.append(f"  {sub_label}: {sub_prose}")
        else:
            lines.append(f"\n{label}\n{prose}")
    return "\n".join(lines)


# ─── الدوال العامة — تُستدعى من signals.py ──────────────────

def generate_brd_from_schema(
    filled_schema: Dict[str, Any],
    *,
    document_id: int,
    project_name: str = "",
    output_subdir: str = "pending",
) -> Tuple[str, str, Dict[str, Any]]:
    """يولّد وثيقة BRD."""
    return _run_generation(
        filled_schema,
        document_id,
        doc_type="BRD",
        project_name=project_name,
        output_subdir=output_subdir,
    )


def generate_mom_from_schema(
    filled_schema: Dict[str, Any],
    *,
    document_id: int,
    project_name: str = "",
    output_subdir: str = "pending",
) -> Tuple[str, str, Dict[str, Any]]:
    """يولّد وثيقة MOM."""
    return _run_generation(
        filled_schema,
        document_id,
        doc_type="MOM",
        project_name=project_name,
        output_subdir=output_subdir,
    )