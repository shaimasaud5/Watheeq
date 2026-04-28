
import os
import re
import json
import requests
from typing import Optional, Any

from .prompts import build_brd_prompt
from .mom_prompts import build_mom_extraction_prompt
from .mom_post_processing import post_process_mom

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "llama3.2"
REQUEST_TIMEOUT = 350  # seconds


def safe_json_loads(text: str) -> Optional[Any]:
    """
    Try to safely extract JSON from a raw LLM response string.
    Returns parsed JSON (dict / list) or None.
    """
    if not text:
        return None

    text = text.strip()

    # direct load first
    try:
        return json.loads(text)
    except Exception:
        pass

    # try to find a json object/array inside the text
    m = re.search(r"(\{(?:.*\n?)*\}|\[(?:.*\n?)*\])", text, re.DOTALL)
    if not m:
        return None

    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def call_ollama(prompt: str) -> Optional[str]:
    """
    Call the Ollama HTTP API and return the raw text response.
    Adjust payload according to your Ollama deployment if needed.
    Returns the raw response string or None on error.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0}
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        # keep prints for quick debugging in container logs
        print("OLLAMA HTTP ERROR:", str(e))
        return None

    try:
        data = resp.json()
    except Exception:
        # fallback to raw text if response is not JSON
        raw_text = resp.text or ""
        return raw_text

    # Common keys that might contain model output — adapt if your Ollama returns different shape
    for key in ("response", "text", "output", "result"):
        if key in data and data.get(key):
            val = data.get(key)
            # if it's a list/obj, try to stringify if needed
            if isinstance(val, (dict, list)):
                try:
                    return json.dumps(val, ensure_ascii=False)
                except Exception:
                    return str(val)
            return str(val)

    # If no known key found, try to stringify whole payload
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return str(data)


def load_mom_schema() -> dict:
    """
    Load mom_schema.json from the extract app directory.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(current_dir, "mom_schema.json")

    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_brd_with_llm(template: dict, transcript: str) -> Optional[dict]:
    """
    Existing BRD extraction logic (kept behaviorally compatible).
    Returns parsed dict or None.
    """
    prompt = build_brd_prompt(template, transcript)

    raw = call_ollama(prompt)
    if raw is None:
        return None

    print("RAW RESPONSE (BRD):", (raw[:1000] + '...') if len(raw) > 1000 else raw)

    parsed = safe_json_loads(raw)
    return parsed if isinstance(parsed, dict) else None


def extract_mom_with_llm(transcript: str) -> dict:
    """
    Build prompt, call LLM, parse JSON, post-process and return cleaned MOM.
    Returns a cleaned dict matching mom_post_processing.get_default_mom_structure() shape.
    """
    schema = load_mom_schema()
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)

    prompt = build_mom_extraction_prompt(transcript, schema_text)

    raw = call_ollama(prompt)
    if raw is None:
        # return empty structure via post_process_mom on empty dict to ensure schema safety
        return post_process_mom({})

    # Try to parse robustly
    parsed = safe_json_loads(raw)
    if parsed is None:
        # Last resort: if raw looks like plain JSON-like dict string, attempt json.loads again
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {}

    # Only accept dict as parsed LLM output; otherwise use empty dict
    if not isinstance(parsed, dict):
        parsed = {}

    cleaned = post_process_mom(parsed)
    return cleaned