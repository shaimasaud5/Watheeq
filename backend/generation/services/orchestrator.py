# generation/services/orchestrator.py
# ─────────────────────────────────────
# يرسل السكيما كاملة للـ LLM في call واحد.
# النموذج يرى كل السياق ويكتب الوثيقة بالكامل.
# بعد الرد: نفككه → نتحقق من الأقسام → نبني .docx

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from docx import Document

from .prompting import build_brd_prompt, build_mom_prompt, key_to_label
from .llm_client import generate_text
from .docx_renderer import build_doc_from_json


class GenerationError(Exception):
    pass


# ── الأقسام المتوقعة لكل نوع وثيقة ─────────────────────────
# الترتيب هنا هو ترتيب الظهور في الوثيقة النهائية
BRD_SECTIONS = [
    "executive_summary",
    "business_drivers",
    "project_scope",
    "stakeholders",
    "current_process",
    "functional_requirements",
    "non_functional_requirements",
    "risk_analysis",
    "glossary",
    "references",
    "appendix",
]

MOM_SECTIONS = [
    "attendees",
    "agenda",
    "discussion_summary",
    "decisions",
    "action_items",
    "next_meeting",
    "notes",
]


# ═══════════════════════════════════════════════════════════════
# تفكيك رد النموذج
# ═══════════════════════════════════════════════════════════════

def _parse_llm_response(response: str) -> Dict[str, Any]:
    """
    يفكك رد النموذج إلى dict منظم.

    الرد يأتي بهذا الشكل:
        [SECTION: executive_summary]
        [FIELD: problem]
        النص هنا...
        [FIELD: expected_benefits]
        - نقطة 1
        - نقطة 2

        [SECTION: stakeholders]
        - stakeholder 1
        - stakeholder 2

        [SECTION: functional_requirements]
        [ITEM]
        Title: ...
        Priority: ...
        Description: ...
        ---

    يرجع:
        {
            "executive_summary": {
                "problem": "النص...",
                "expected_benefits": ["نقطة 1", "نقطة 2"]
            },
            "stakeholders": ["stakeholder 1", "stakeholder 2"],
            "functional_requirements": [
                {"title": "...", "priority": "High", "description": "..."}
            ]
        }
    """
    result = {}

    # نقسم الرد على [SECTION: ...] tags
    section_pattern = re.compile(r'\[SECTION:\s*(\w+)\]', re.IGNORECASE)
    section_splits   = section_pattern.split(response)

    # section_splits = [text_before, section_name, section_content, section_name, ...]
    # نتجاهل أول عنصر (نص قبل أول section)
    i = 1
    while i < len(section_splits) - 1:
        section_name    = section_splits[i].strip().lower()
        section_content = section_splits[i + 1] if i + 1 < len(section_splits) else ""
        result[section_name] = _parse_section(section_name, section_content)
        i += 2

    return result


def _parse_section(section_name: str, content: str) -> Any:
    """
    يفكك محتوى قسم واحد.

    ثلاثة أنواع ممكنة:
    1. قسم فيه FIELD tags → dict
    2. قسم فيه ITEM tags → list of dicts
    3. قسم فيه bullet points فقط → list of strings
    """
    content = content.strip()
    if not content:
        return None

    # النوع 1: قسم فيه [FIELD: ...] tags
    if '[FIELD:' in content:
        return _parse_field_section(content)

    # النوع 2: قسم فيه [ITEM] tags
    if '[ITEM]' in content:
        return _parse_item_section(content)

    # النوع 3: قائمة bullet points أو نص عادي
    return _parse_simple_section(content)


def _parse_field_section(content: str) -> Dict[str, Any]:
    """
    يفكك قسماً فيه [FIELD: ...] tags.
    مثال: executive_summary, business_drivers, project_scope
    """
    result = {}
    field_pattern = re.compile(r'\[FIELD:\s*(\w+)\]', re.IGNORECASE)
    field_splits   = field_pattern.split(content)

    # نتجاهل أول عنصر
    i = 1
    while i < len(field_splits) - 1:
        field_name    = field_splits[i].strip().lower()
        field_content = field_splits[i + 1] if i + 1 < len(field_splits) else ""
        field_content = field_content.strip()

        if not field_content:
            i += 2
            continue

        # لو المحتوى قائمة bullet points
        if field_content.startswith('-'):
            result[field_name] = _parse_bullets(field_content)
        else:
            result[field_name] = field_content

        i += 2

    return result if result else None


def _parse_item_section(content: str) -> List[Dict[str, Any]]:
    """
    يفكك قسماً فيه [ITEM] tags.
    مثال: functional_requirements, risk_analysis, action_items, glossary
    """
    items = []

    # نقسم على [ITEM] ثم على --- بين العناصر
    raw_items = re.split(r'\[ITEM\]', content)

    for raw_item in raw_items:
        raw_item = raw_item.strip()
        if not raw_item:
            continue

        # نزيل --- الفاصل في نهاية كل عنصر
        raw_item = raw_item.rstrip('-').strip()
        if not raw_item:
            continue

        item = {}
        # كل سطر فيه "Key: Value"
        for line in raw_item.splitlines():
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                key, _, value = line.partition(':')
                key   = key.strip().lower().replace(' ', '_')
                value = value.strip()
                if key and value:
                    item[key] = value

        if item:
            items.append(item)

    return items if items else None


def _parse_simple_section(content: str) -> Any:
    """
    يفكك قسماً بسيطاً:
    - لو يبدأ بـ "-" → قائمة bullet points
    - غير ذلك → نص عادي
    """
    if content.startswith('-'):
        return _parse_bullets(content)
    return content


def _parse_bullets(content: str) -> List[str]:
    """يستخرج قائمة bullet points من النص."""
    bullets = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('- '):
            bullets.append(line[2:].strip())
        elif line.startswith('-'):
            bullets.append(line[1:].strip())
    return [b for b in bullets if b]


# ═══════════════════════════════════════════════════════════════
# التحقق من الأقسام الناقصة
# ═══════════════════════════════════════════════════════════════

def _get_missing_sections(
    parsed:       Dict[str, Any],
    filled_schema: Dict[str, Any],
    doc_type:     str,
) -> List[str]:
    """
    يتحقق من الأقسام الناقصة في رد النموذج.

    يعتبر القسم "ناقصاً" فقط لو:
    - موجود في السكيما الأصلية وفيه بيانات
    - غير موجود في رد النموذج أو قيمته None
    """
    expected = BRD_SECTIONS if doc_type == "BRD" else MOM_SECTIONS
    missing  = []

    for section in expected:
        # لو القسم في السكيما فارغ → طبيعي أن يغيب
        schema_value = filled_schema.get(section)
        if _is_empty(schema_value):
            continue

        # لو القسم غائب من رد النموذج → ناقص
        if section not in parsed or _is_empty(parsed.get(section)):
            missing.append(section)

    return missing


def _is_empty(value: Any) -> bool:
    """يتحقق من كل حالات الفراغ."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in ("", "null", "none", "n/a", "-"):
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _fetch_missing_section(
    section_name:  str,
    schema_value:  Any,
    doc_type:      str,
) -> Any:
    """
    يطلب من النموذج قسماً واحداً ناقصاً في call منفصل صغير.
    يُستخدم فقط لو التحقق اكتشف قسماً ناقصاً.
    """
    import json
    label       = key_to_label(section_name)
    schema_text = json.dumps({section_name: schema_value}, ensure_ascii=False, indent=2)

    prompt = f"""You are writing one section of a {doc_type} document.

Section: {label}
Data: {schema_text}

Write this section using the same format rules:
- For text fields: 1-8 professional sentences, no bullet points.
- For list fields: each item on its own line starting with "- ", 1-3 sentences each.
- For item fields: use Title/Description/Priority format, separate with ---.
- Do NOT add information not in the data.
- Start directly with the content, no introduction.

Output:"""

    raw    = generate_text(prompt)
    parsed = _parse_section(section_name, raw)
    return parsed


# ═══════════════════════════════════════════════════════════════
# دالة التوليد الرئيسية
# ═══════════════════════════════════════════════════════════════

def _run_generation(
    filled_schema: Dict[str, Any],
    document_id:   int,
    doc_type:      str,
    project_name:  str = "",
    output_subdir: str = "pending",
    cover_meta:    Dict[str, str] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    الخطوات:
    1. يرسل السكيما كاملة للـ LLM في call واحد
    2. يفكك الرد
    3. يتحقق من الأقسام الناقصة ويطلبها
    4. يبني .docx
    5. يحفظه في media/
    """
    if not isinstance(filled_schema, dict) or not filled_schema:
        raise GenerationError("filled_schema must be a non-empty JSON object.")

    start = time.time()

    # ── الخطوة 1: call واحد للـ LLM ─────────────────────────────
    print(f"[Generation] Sending full schema to LLM — single call...")
    if doc_type == "BRD":
        prompt = build_brd_prompt(filled_schema)
    else:
        prompt = build_mom_prompt(filled_schema)

    raw_response = generate_text(prompt)

    # ── الخطوة 2: تفكيك الرد ────────────────────────────────────
    parsed = _parse_llm_response(raw_response)
    print(f"[Generation] Parsed sections: {list(parsed.keys())}")

    # ── الخطوة 3: التحقق من الأقسام الناقصة ─────────────────────
    missing = _get_missing_sections(parsed, filled_schema, doc_type)

    if missing:
        print(f"[Generation] Missing sections: {missing} — fetching individually...")
        for section_name in missing:
            schema_value = filled_schema.get(section_name)
            fetched      = _fetch_missing_section(section_name, schema_value, doc_type)
            if fetched:
                parsed[section_name] = fetched
                print(f"[Generation] Fetched: {section_name}")

    # ── الخطوة 4: ترتيب الأقسام ─────────────────────────────────
    section_order = BRD_SECTIONS if doc_type == "BRD" else MOM_SECTIONS
    ordered       = {}
    for section in section_order:
        if section in parsed and not _is_empty(parsed[section]):
            ordered[section] = parsed[section]

    if not ordered:
        raise GenerationError("No content was generated.")

    elapsed = time.time() - start

    # ── الخطوة 5: نص بسيط للحفظ في DB ──────────────────────────
    generated_text = _build_plain_text(ordered, doc_type)

    # ── الخطوة 6: حفظ .docx ─────────────────────────────────────
    rel_dir = (output_subdir or "pending").strip("/\\") or "pending"
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    filename = f"{doc_type.lower()}_{document_id}_{int(time.time() * 1000)}.docx"
    rel_path = f"{rel_dir}/{filename}"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    doc = Document()
    build_doc_from_json(doc, ordered, doc_type, project_name, cover_meta or {})
    doc.save(abs_path)

    print(f"[Generation] Done in {elapsed:.1f}s → {rel_path}")

    meta = {
        "model":           "llama-3.3-70b-versatile",
        "elapsed_seconds": round(elapsed, 3),
    }

    return generated_text, rel_path, meta


def _build_plain_text(ordered: Dict[str, Any], doc_type: str) -> str:
    """يبني نسخة نصية بسيطة للحفظ في قاعدة البيانات."""
    title = "Business Requirements Document" if doc_type == "BRD" else "Minutes of Meeting"
    lines = [f"{title}\n"]

    for key, value in ordered.items():
        label = key_to_label(key)
        if isinstance(value, str):
            lines.append(f"\n{label}\n{value}")
        elif isinstance(value, list):
            lines.append(f"\n{label}")
            for item in value:
                if isinstance(item, dict):
                    lines.append("  - " + ", ".join(f"{k}: {v}" for k, v in item.items()))
                else:
                    lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"\n{label}")
            for sub_key, sub_val in value.items():
                sub_label = key_to_label(sub_key)
                if isinstance(sub_val, list):
                    lines.append(f"  {sub_label}:")
                    for item in sub_val:
                        lines.append(f"    - {item}")
                else:
                    lines.append(f"  {sub_label}: {sub_val}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# الدوال العامة — تُستدعى من signals.py و views.py
# ═══════════════════════════════════════════════════════════════

def generate_brd_from_schema(
    filled_schema: Dict[str, Any],
    *,
    document_id:   int,
    project_name:  str = "",
    output_subdir: str = "pending",
    cover_meta:    Dict[str, str] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """يولّد وثيقة BRD."""
    return _run_generation(
        filled_schema, document_id,
        doc_type="BRD", project_name=project_name,
        output_subdir=output_subdir, cover_meta=cover_meta,
    )


def generate_mom_from_schema(
    filled_schema: Dict[str, Any],
    *,
    document_id:   int,
    project_name:  str = "",
    output_subdir: str = "pending",
    cover_meta:    Dict[str, str] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """يولّد وثيقة MOM."""
    return _run_generation(
        filled_schema, document_id,
        doc_type="MOM", project_name=project_name,
        output_subdir=output_subdir, cover_meta=cover_meta,
    )