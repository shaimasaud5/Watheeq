# extract/llm_service.py
# ───────────────────────
# يرسل prompt لـ Ollama لاستخراج قيمة فقرة واحدة من السكيما.

import json
import re
import requests
from typing import Optional

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "llama3.2"


def _call_ollama(prompt: str) -> Optional[str]:
    """يرسل prompt لـ Ollama ويرجع النص الخام."""
    payload = {
        "model":   MODEL_NAME,
        "prompt":  prompt,
        "stream":  False,
        "format":  "json",
        "options": {"temperature": 0},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=None)
        resp.raise_for_status()
        data = resp.json()
        for key in ("response", "text", "output", "result"):
            if data.get(key):
                val = data[key]
                if isinstance(val, (dict, list)):
                    return json.dumps(val, ensure_ascii=False)
                return str(val)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        print(f"OLLAMA ERROR: {e}")
        return None


def _safe_parse(text: str) -> Optional[dict]:
    """يحاول استخراج JSON من رد الـ LLM."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"(\{(?:.*\n?)*\})", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def extract_section(section_name: str, section_template, context: str, doc_type: str = "BRD") -> Optional[dict]:
    """
    يرسل للـ LLM:
    - اسم الفقرة (section_name)
    - الهيكل المطلوب (section_template)
    - أقرب 3 chunks من الترانسكريبت (context)

    يطلب منه ملء الفقرة من النص المعطى فقط.
    يرجع dict بنفس هيكل section_template.
    """
    template_str = json.dumps({section_name: section_template}, ensure_ascii=False, indent=2)

    if doc_type == "MOM":
        persona = "expert meeting minutes analyst extracting structured information from meeting transcripts"
        focus   = "Focus on: decisions, action items, attendees, agenda, discussion points."
    else:
        persona = "expert business analyst extracting structured requirements from meeting transcripts"
        focus   = "Focus on: requirements, scope, stakeholders, risks, objectives."

    prompt = f"""You are an {persona}.

TASK:
Fill in the following JSON section using ONLY the information found in the provided transcript excerpts.
{focus}
Do NOT add information that is not in the transcript.
If information is not found, use null for strings and [] for arrays.

SECTION TO FILL:
{template_str}

TRANSCRIPT EXCERPTS:
{context}

RULES:
1. Return ONLY valid JSON matching the exact structure above.
2. Do NOT add extra fields.
3. Do NOT add explanations or text outside the JSON.
4. Use null for missing string values.
5. Use [] for missing array values.

JSON OUTPUT:"""

    raw    = _call_ollama(prompt)
    parsed = _safe_parse(raw)
    if isinstance(parsed, dict):
        return parsed
    return None
