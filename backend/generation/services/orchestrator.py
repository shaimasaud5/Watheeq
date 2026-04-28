# generation/services/orchestrator.py
# -------------------------------------
# The "brain" of the generation process.
# Connects everything: schema → LLM → renderer → saved file.
#
# TWO PUBLIC FUNCTIONS (called from views.py):
#   generate_brd_from_schema() — for BRD
#   generate_mom_from_schema() — for MoM
#
# Both call the shared _run_generation() function internally.
#
# CHANGE LOG:
#   - Added project_name parameter to public functions and _run_generation()
#     so the cover page shows the project name from the database instead of
#     trying to extract it from the schema (which was unreliable).
#   - project_name is passed through to build_doc_from_json() in the renderer.

import os
import time
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from docx import Document

from .prompting import (
    build_field_prompt,
    key_to_label,
    value_to_raw_text,
    get_token_limit,
    should_skip_llm,
    is_structural,
)
from .llm_client import LLMConfig, OllamaLLMClient
from .docx_renderer import build_doc_from_json


class GenerationError(Exception):
    pass


# -------------------------------------------------------------------
# Preamble phrases the LLM sometimes adds despite being told not to.
# We drop any output line that starts with one of these.
# -------------------------------------------------------------------
_PREAMBLE_STARTS = (
    "here is", "here's", "sure,", "sure!", "certainly,", "of course",
    "this section", "below is", "the following", "as requested",
    "based on", "i will", "i'll", "please find", "in this section",
    "this document", "the document", "note:", "note that", "as a senior",
)


def _clean_llm_output(text: str) -> str:
    """
    Cleans the raw LLM response:
      - Removes preamble lines
      - Removes markdown headers (lines starting with #)
      - Removes divider lines (--- or ===)
      - Joins remaining lines into one clean paragraph
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
    Returns True if a dict contains at least one plain string value.

    This detects the pattern girl 3 uses for text sections:
        "executive_summary": {
            "problem": "Declining retention",       ← string → LLM
            "proposed_solution": "Analytics platform" ← string → LLM
            "expected_benefits": ["15%", "Speed"]   ← list → renderer
        }

    A dict that has ONLY lists/dicts as values (like document_control)
    returns False — it is purely structural and goes straight to renderer.
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
    SHARED INTERNAL FUNCTION — does the actual generation work.

    Parameters:
        filled_schema - the extracted JSON from the database
        document_id   - used for naming the output .docx file
        doc_type      - "BRD" or "MOM"
        project_name  - name of the linked Project from the database.
                        Shown on the cover page. Falls back to schema
                        extraction if empty.
        output_subdir - media subfolder for writing the generated file.
                        Use "pending" for review files, "documents" for final.

    Steps:
      1. Connect to Ollama
      2. Loop over each schema field using shape-based dispatch
      3. Call renderer to build the Word document
      4. Return results
    """
    if not isinstance(filled_schema, dict) or not filled_schema:
        raise GenerationError("filled_schema must be a non-empty JSON object.")

    base_url    = os.getenv("OLLAMA_BASE_URL",    "http://ollama:11434")
    model       = os.getenv("OLLAMA_MODEL",       "llama3")
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))

    client = OllamaLLMClient(LLMConfig(
        base_url=base_url,
        model=model,
        temperature=temperature,
    ))

    start = time.time()

    expanded: Dict[str, Any] = {}

    for field_key, field_value in filled_schema.items():

        # Skip completely empty fields
        if field_value in (None, "", [], {}):
            continue

        # --- CASE 1: known always-structural fields (document_control, meeting_info) ---
        # Renderer shows them as blocks directly. No LLM needed.
        if field_key in ("document_control", "meeting_info"):
            expanded[field_key] = ""
            continue

        # --- CASE 2: dict whose values are strings (e.g. executive_summary from girl 3) ---
        # girl 3 wraps text fields in dicts:
        #   "executive_summary": {"problem": "...", "proposed_solution": "..."}
        # Each string sub-field is sent to the LLM individually.
        # The renderer will show: Heading1 (executive_summary) +
        #                         Heading2 (problem) + prose
        #                         Heading2 (proposed_solution) + prose
        if isinstance(field_value, dict) and _dict_has_string_values(field_value):
            sub_expanded = {}
            for sub_key, sub_val in field_value.items():
                if not sub_val or not isinstance(sub_val, str):
                    continue
                prompt      = build_field_prompt(sub_key, sub_val, doc_type=doc_type)
                token_limit = get_token_limit(sub_key)
                raw         = client.generate_text(prompt, max_tokens=token_limit)
                prose       = _clean_llm_output(raw)
                if len(prose) < 10:
                    prose = sub_val
                sub_expanded[sub_key] = prose
            expanded[field_key] = sub_expanded
            continue

        # --- CASE 3: structural value (pure dict-of-lists, list-of-dicts, list-of-strings) ---
        # Renderer handles these as blocks/bullets directly.
        if is_structural(field_value):
            expanded[field_key] = ""
            continue

        # --- CASE 4: plain string → LLM writes prose ---
        prompt      = build_field_prompt(field_key, field_value, doc_type=doc_type)
        token_limit = get_token_limit(field_key)
        raw         = client.generate_text(prompt, max_tokens=token_limit)
        prose       = _clean_llm_output(raw)

        if len(prose) < 10:
            prose = value_to_raw_text(field_value)

        expanded[field_key] = prose

    if not expanded:
        raise GenerationError("LLM returned empty output for every field.")

    elapsed = time.time() - start

    # Plain-text version stored in doc.content in the database
    generated_text = _build_plain_text(expanded, doc_type)

    # Save the .docx file
    rel_dir  = (output_subdir or "pending").strip("/\\")
    if not rel_dir:
        rel_dir = "pending"
    abs_dir  = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)

    if rel_dir == "pending":
        filename = f"{doc_type.lower()}_{document_id}_{int(time.time() * 1000)}.docx"
    else:
        filename = f"{doc_type.lower()}_{document_id}.docx"
    rel_path = f"{rel_dir}/{filename}"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)

    doc = Document()
    build_doc_from_json(doc, filled_schema, expanded, doc_type, project_name)
    doc.save(abs_path)

    meta = {
        "model":           model,
        "temperature":     temperature,
        "elapsed_seconds": round(elapsed, 3),
    }

    return generated_text, rel_path, meta


def _build_plain_text(expanded: Dict[str, Any], doc_type: str) -> str:
    """Plain-text version of the document stored in doc.content."""
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


# -------------------------------------------------------------------
# PUBLIC FUNCTIONS — called from views.py
# -------------------------------------------------------------------

def generate_brd_from_schema(
    filled_schema: Dict[str, Any],
    *,
    document_id: int,
    project_name: str = "",
    output_subdir: str = "pending",
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Generates a BRD Word document.
    Called by views.py when doc.doc_type == 'BRD'.

    project_name — pass doc.project.name from views.py so the cover page
                   shows the real project name from the database.
    """
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
    """
    Generates a MoM Word document.
    Called by views.py when doc.doc_type == 'MOM'.

    project_name — pass doc.project.name from views.py so the cover page
                   shows the real project name from the database.
    """
    return _run_generation(
        filled_schema,
        document_id,
        doc_type="MOM",
        project_name=project_name,
        output_subdir=output_subdir,
    )
