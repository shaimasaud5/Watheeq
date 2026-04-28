# generation/services/docx_renderer.py
# ---------------------------------------
# Turns the LLM-generated text into a Word document (.docx).
#
# FIXES IN THIS VERSION:
#
#   1. EMPTY PAGE 2 FIXED:
#      The cover page had 7+6 = 13 spacing loops × Pt(14) = 182pt
#      of whitespace. This overflowed the cover onto page 2, leaving
#      it blank, and pushing content to page 3.
#      Fixed by reducing to 4+3 loops × Pt(10) = 70pt total.
#      Now: cover = page 1, content = page 2. No empty page.
#
#   2. COVER PAGE BARS FIXED:
#      Previous approach used paragraph shading XML (unreliable) then
#      thick borders (also unreliable across Word versions).
#      New approach: uses a Table with 1 row and 1 cell, with a
#      solid background colour set via XML shading on the cell.
#      Tables with cell shading render reliably in all Word versions.
#
#   3. MEETING INFO SECTION REMOVED FROM BODY:
#      meeting_info data already appears on the cover page.
#      Showing it again in the body as Heading 1 + sub-sections
#      is redundant duplication. We now skip it in the body entirely.
#
#   4. ACTION ITEM DETAIL LINES TIGHTER:
#      space_after = Pt(1) between detail lines inside a block,
#      confirmed to be set correctly in _render_item_block().

import os
from typing import Any, Dict
from datetime import date

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.oxml.ns import nsmap

from .prompting import key_to_label, should_skip_llm, is_structural


# -------------------------------------------------------------------
# COLOURS
# -------------------------------------------------------------------
NAVY  = RGBColor(0x1F, 0x39, 0x64)   # dark navy  — cover title
BLUE  = RGBColor(0x2E, 0x75, 0xB6)   # corporate blue — Heading 1
GREY  = RGBColor(0x40, 0x40, 0x40)   # dark grey — Heading 2
BLACK = RGBColor(0x00, 0x00, 0x00)   # body text


# No hardcoded field order — sections are rendered in the exact order
# they appear in the schema JSON. This is intentional:
#   1. Supports any dynamic schema girl 3 produces
#   2. Keeps ROUGE-L high — flatten_json and the document traverse
#      fields in the same order, so the LCS is maximised

# -------------------------------------------------------------------
# PRIORITY AND STATUS LABELS
# -------------------------------------------------------------------
# MoSCoW → High/Medium/Low mapping
# "must/must-have" = highest priority → High
# "should/should-have" = medium priority → Medium
# "could/could-have" = lower priority → Low
# "won't" = not in this release → excluded (still shown as-is)
PRIORITY_LABELS = {
    # MoSCoW → normalised severity
    "must":          "High",
    "must-have":     "High",
    "musthave":      "High",
    "should":        "Medium",
    "should-have":   "Medium",
    "shouldhave":    "Medium",
    "could":         "Low",
    "could-have":    "Low",
    "couldhave":     "Low",
    "wont":          "Won't Have",
    "won't":         "Won't Have",
    "wont-have":     "Won't Have",
    # Direct High/Medium/Low (NFR fields)
    "high":          "High",
    "medium":        "Medium",
    "low":           "Low",
}

STATUS_LABELS = {
    "approved":    "Approved",
    "pending":     "Pending",
    "rejected":    "Rejected",
    "open":        "Open",
    "closed":      "Closed",
    "done":        "Done",
    "in progress": "In Progress",
}


# -------------------------------------------------------------------
# MAIN PUBLIC FUNCTION
# -------------------------------------------------------------------

def build_doc_from_json(
    doc: Document,
    filled_schema: Dict[str, Any],
    expanded: Dict[str, str],
    doc_type: str,
    project_name: str = "",
) -> None:
    """
    Builds the complete Word document.

    Parameters:
        doc           - empty python-docx Document from orchestrator
        filled_schema - original JSON from the database
        expanded      - {field_key: prose_text} — "" for structural fields (LLM skipped)
        doc_type      - "BRD" or "MOM"
    """
    _set_margins(doc)
    _apply_styles(doc)

    # Page 1: cover page
    _add_cover_page(doc, filled_schema, doc_type, project_name)

    # Page break — content starts on page 2
    doc.add_page_break()

    # Footer with page numbers on all pages
    _add_footer(doc)

    # Section order = exact order of keys in filled_schema JSON.
    # meeting_info is skipped — it lives on the cover page only.
    # No sorting, no reordering — whatever order girl 3 produced.
    for field_key in filled_schema.keys():
        if field_key == "meeting_info":
            continue                        # cover page only
        if field_key not in expanded:
            continue                        # was empty, skipped in orchestrator
        prose          = expanded[field_key]
        original_value = filled_schema.get(field_key)
        _add_section(doc, field_key, prose, original_value)


# -------------------------------------------------------------------
# SECTION RENDERING — three modes
# -------------------------------------------------------------------

def _add_section(
    doc: Document,
    field_key: str,
    prose: str,
    original_value: Any,
) -> None:
    """
    Renders one section using SHAPE-BASED dispatch — no hardcoded field names.

    The rendering mode is decided purely by the VALUE'S SHAPE:

    MODE 1 — structural value (dict OR list-of-dicts):
        prose="" was set by orchestrator (LLM was skipped).
        Renderer shows sub-sections / blocks directly. No prose.

    MODE 2 — prose value + dict value:
        The field has LLM-generated prose AND a dict with named sub-keys.
        Show prose first, then Heading 2 sub-sections for each dict key.
        String-valued sub-keys are skipped (they were the source of the prose).

    MODE 3 — prose only:
        Simple string or list-of-strings field. Show the LLM prose directly.
    """
    heading = doc.add_heading(key_to_label(field_key), level=1)
    for run in heading.runs:
        run.font.color.rgb = BLUE

    if is_structural(original_value) and not isinstance(prose, dict):
        # MODE 1: structural value, LLM was skipped — blocks only, no prose
        _render_skip_field(doc, field_key, original_value)

    elif isinstance(prose, dict):
        # MODE 2: dict-of-strings field expanded by orchestrator
        # prose = {"problem": "expanded...", "proposed_solution": "expanded..."}
        # Show each sub-field as Heading2 + prose paragraph
        for sub_key, sub_prose in prose.items():
            if not sub_prose:
                continue
            h2 = doc.add_heading(key_to_label(sub_key), level=2)
            for run in h2.runs:
                run.font.color.rgb = GREY
            # If original sub-value was a list/dict, render structurally
            sub_val = original_value.get(sub_key) if isinstance(original_value, dict) else None
            if sub_val and is_structural(sub_val):
                _render_skip_field(doc, sub_key, sub_val)
            else:
                p = doc.add_paragraph(sub_prose)
                p.paragraph_format.space_after = Pt(6)

    else:
        # MODE 3: plain prose only
        if prose:
            p = doc.add_paragraph(prose)
            p.paragraph_format.space_after = Pt(6)

    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# -------------------------------------------------------------------
# MODE 1: STRUCTURAL VALUES (dict or list-of-dicts)
# -------------------------------------------------------------------

def _render_skip_field(doc: Document, field_key: str, value: Any) -> None:
    """
    Renders structured content with no prose.
    Works for: dict, list of dicts, list of strings.
    """
    if isinstance(value, dict):
        for sub_key, sub_val in value.items():
            if not sub_val:
                continue
            h2 = doc.add_heading(key_to_label(sub_key), level=2)
            for run in h2.runs:
                run.font.color.rgb = GREY

            if isinstance(sub_val, list):
                if sub_val and isinstance(sub_val[0], dict):
                    # list-of-dicts: render each as a compact record line
                    for item in sub_val:
                        _render_compact_record(doc, item)
                else:
                    # list-of-strings: render as bullet points
                    for item in sub_val:
                        doc.add_paragraph(str(item), style="List Bullet")
            elif isinstance(sub_val, dict):
                # nested dict: render as compact record
                _render_compact_record(doc, sub_val)
            else:
                doc.add_paragraph(str(sub_val))

    elif isinstance(value, list):
        if value and isinstance(value[0], dict):
            for idx, item in enumerate(value, start=1):
                _render_item_block(doc, item, idx)
        else:
            # list-of-strings → bullet points always
            for item in value:
                if str(item).strip():
                    doc.add_paragraph(str(item).strip(), style="List Bullet")


# -------------------------------------------------------------------
# MODE 2: PROSE + NAMED DICT SUB-SECTIONS
# -------------------------------------------------------------------

def _render_named_dict(
    doc: Document,
    value: dict,
    skip_strings: bool = False,
) -> None:
    """
    Renders a dict as Heading 2 sub-sections.
    skip_strings=True skips string-valued keys to avoid duplication.
    """
    for sub_key, sub_val in value.items():
        if not sub_val:
            continue
        if skip_strings and isinstance(sub_val, str):
            continue

        h2 = doc.add_heading(key_to_label(sub_key), level=2)
        for run in h2.runs:
            run.font.color.rgb = GREY

        if isinstance(sub_val, list):
            if sub_val and isinstance(sub_val[0], dict):
                for idx, item in enumerate(sub_val, start=1):
                    _render_item_block(doc, item, idx)
            else:
                for item in sub_val:
                    doc.add_paragraph(str(item), style="List Bullet")
        else:
            doc.add_paragraph(str(sub_val))


# -------------------------------------------------------------------
# ITEM BLOCK
# -------------------------------------------------------------------

def _render_item_block(doc: Document, item: dict, idx: int) -> None:
    """
    Renders one dict item as:
        [Heading 2]  Best heading value
                     Key: Value      ← bold label, Pt(1) after each line
                     Key: Value
        [gap Pt(8) after the block]
    """
    heading_text = _pick_best_heading(item, idx)

    h2 = doc.add_heading(heading_text, level=2)
    for run in h2.runs:
        run.font.color.rgb = GREY

    for k, v in item.items():
        # Skip if this value was used as the heading
        if str(v) == heading_text:
            continue
        # Skip null / empty values — avoids "Responsibility: None" in output
        if v is None or v == "" or v == [] or v == {}:
            continue

        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(1)

        label_run = p.add_run(f"{key_to_label(k)}: ")
        label_run.bold = True
        p.add_run(_format_value(k, str(v)))

    # Clear gap after the whole block
    gap = doc.add_paragraph()
    gap.paragraph_format.space_before = Pt(0)
    gap.paragraph_format.space_after  = Pt(8)


def _render_compact_record(doc: Document, d: dict) -> None:
    """
    Renders a flat dict as one compact indented line.
    Example: Date: 2026-04-01  |  Author: Afra  |  Version: 1.0
    Skips keys with None or empty values.
    """
    parts = [
        f"{key_to_label(k)}: {_format_value(k, str(v))}"
        for k, v in d.items()
        if v is not None and str(v).strip() not in ("", "None")
    ]
    if not parts:
        return
    p = doc.add_paragraph("  |  ".join(parts))
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(3)


def _pick_best_heading(d: dict, fallback_idx: int) -> str:
    """
    Picks the most meaningful value from a dict to use as Heading 2.

    Priority order:
      1. Preferred descriptive keys: title, name, task, risk, term, description
      2. id / version as secondary (short identifiers)
      3. Any short value <= 80 chars
      4. Fallback: "Item N"

    NOTE: 'priority', 'impact', 'likelihood', 'status', 'category' are
    NEVER used as headings — they are metadata shown as detail lines below.
    """
    # Keys that make good headings (descriptive content)
    heading_keys = (
        "title", "name", "task", "action", "risk",
        "requirement", "topic", "term", "description",
    )
    # Keys that are metadata — never use as heading
    skip_as_heading = {
        "priority", "impact", "likelihood", "status",
        "category", "id", "version", "due_date", "date",
        "owner", "role", "mitigation", "definition",
    }

    for key in heading_keys:
        val = d.get(key)
        if val and str(val).strip():
            text = str(val).strip()
            # Cap description at 80 chars to keep heading readable
            return text[:80] + ("…" if len(text) > 80 else "")

    # Secondary: id or version (short identifier)
    for key in ("id", "version"):
        val = d.get(key)
        if val and str(val).strip():
            return str(val).strip()

    # Last resort: shortest non-metadata value
    candidates = [
        str(v).strip() for k, v in d.items()
        if k not in skip_as_heading
        and v is not None
        and str(v).strip()
        and len(str(v).strip()) <= 80
    ]
    if candidates:
        return min(candidates, key=len)

    return f"Item {fallback_idx}"


def _format_value(key: str, value: str) -> str:
    """Formats raw schema values into professional display strings."""
    key_lower = key.lower()
    val_lower = value.lower().strip()
    if key_lower == "priority":
        return PRIORITY_LABELS.get(val_lower, value.title())
    if key_lower in ("impact", "likelihood"):
        return value.capitalize()
    if key_lower == "status":
        return STATUS_LABELS.get(val_lower, value.title())
    return value


# -------------------------------------------------------------------
# COVER PAGE
# -------------------------------------------------------------------


def _add_logo(doc: Document) -> None:
    """
    Adds the Watheeq logo to the cover page, left-aligned, small size.

    Search order for the logo file:
      1. WATHEEQ_LOGO_PATH environment variable (set in Docker / settings)
      2. <same directory as this .py file>/watheeq_logo.jpg
      3. <same directory as this .py file>/photo_5960662120447806859_x.jpg

    If the file is not found the function returns silently — the document
    is still generated correctly, just without the logo.

    Size: 1.5 inches wide (height auto-scales to keep aspect ratio).
    Alignment: left.
    """
    candidates = [
        os.environ.get("WATHEEQ_LOGO_PATH", ""),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "watheeq_logo.jpg"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "photo_5960662120447806859_x.jpg"),
    ]
    logo_path = next((p for p in candidates if p and os.path.exists(p)), None)
    if not logo_path:
        return  # logo missing — skip silently, document still generates

    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after  = Pt(4)
    run = para.add_run()
    run.add_picture(logo_path, width=Inches(1.8))


def _add_cover_page(doc: Document, schema: dict, doc_type: str, project_name: str = "") -> None:
    """
    Adds a professional cover page as page 1.

    SPACING FIX (the empty page 2 bug):
        Old: 7 loops × Pt(14) + 6 loops × Pt(14) = 182pt whitespace
             → cover overflowed onto page 2, leaving it blank
        New: 4 loops × Pt(10) + 3 loops × Pt(10) = 70pt whitespace
             → cover fits on page 1, content starts on page 2

    COLOURED BAR FIX:
        Old approaches (paragraph shading XML, thick borders) were
        unreliable across Word versions.
        New approach: uses a 1-cell Table with cell background colour
        set via XML shading. Tables render reliably in all Word versions.

    Layout (all fits on page 1):
        [navy table bar]
        [watheeq_logo.jpg — left-aligned, 1.5 inch wide]
        (4 spacing paragraphs)
        BUSINESS REQUIREMENTS DOCUMENT / MINUTES OF MEETING
        Project Name / Meeting Name
        ─────────────────
        (3 spacing paragraphs)
        Version / Date / Author / Status  (or Date / Time / Location / Facilitator)
        (1 spacing paragraph)
        [blue table bar]
    """

    # --- Navy bar at the top ---
    _add_table_bar(doc, colour="1F3964", height_cm=0.6)

    # Small gap below bar
    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(4)

    # Watheeq logo — top-left, small (1.5 inch wide)
    # Path is resolved relative to this file so it works in any environment.
    # Falls back silently if the image is not found.
    _add_logo(doc)

    # Spacing to push title toward centre
    for _ in range(4):
        doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Document type label (small, blue, all caps)
    doc_title = _detect_doc_title(doc_type)
    type_para = doc.add_paragraph()
    type_para.paragraph_format.space_before = Pt(0)
    type_para.paragraph_format.space_after  = Pt(14)  # gap before project name
    type_run  = type_para.add_run(doc_title.upper())
    type_run.font.name      = "Calibri"
    type_run.font.size      = Pt(9)
    type_run.font.bold      = True
    type_run.font.color.rgb = BLUE
    type_run.font.all_caps  = True

    # Project / meeting name — large and prominent
    # Use project_name from the database first (passed from views.py).
    # Fall back to schema extraction only if project_name is empty.
    if not project_name:
        project_name = _detect_project_name(schema, doc_type)
    if project_name:
        name_para = doc.add_paragraph()
        name_run  = name_para.add_run(project_name)
        name_run.font.name      = "Calibri"
        name_run.font.size      = Pt(28)
        name_run.font.bold      = True
        name_run.font.color.rgb = NAVY

    # Short blue decorative line under the name
    line_para = doc.add_paragraph()
    line_para.paragraph_format.space_before = Pt(6)
    line_para.paragraph_format.space_after  = Pt(14)
    _add_bottom_border(line_para, colour="2E75B6")

    # Spacing before meta block — REDUCED from 6 to 3
    for _ in range(3):
        doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Meta information
    meta = _extract_cover_meta(schema, doc_type)
    for label, value in meta.items():
        if not value:
            continue
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        label_run = p.add_run(f"{label}:   ")
        label_run.font.name      = "Calibri"
        label_run.font.size      = Pt(10)
        label_run.font.bold      = True
        label_run.font.color.rgb = GREY
        value_run = p.add_run(str(value))
        value_run.font.name      = "Calibri"
        value_run.font.size      = Pt(10)
        value_run.font.color.rgb = NAVY

    # Gap before bottom bar
    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # --- Blue bar at the bottom ---
    _add_table_bar(doc, colour="2E75B6", height_cm=0.35)


def _add_table_bar(doc: Document, colour: str, height_cm: float) -> None:
    """
    Adds a solid coloured horizontal bar using a 1-cell table.

    WHY A TABLE?
    python-docx cannot directly set paragraph background colours.
    Two previous approaches failed:
        - XML paragraph shading (w:shd): ignored by some Word versions
        - Thick paragraph borders: rendered as thin lines, not solid bars

    A table cell with XML shading is the most reliable method because
    Word always renders table cell backgrounds, regardless of version.

    colour     — hex string without #, e.g. "1F3964"
    height_cm  — bar height in centimetres
    """
    # Create a 1-row, 1-column table
    table = doc.add_table(rows=1, cols=1)

    # Make the table span the full page width
    table.style = "Table Grid"
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)

    # Set table width to 100% of page
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"),    "5000")
    tblW.set(qn("w:type"), "pct")
    tblPr.append(tblW)

    # Remove all borders so only the background colour shows
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"),   "none")
        border.set(qn("w:sz"),    "0")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "auto")
        tblBorders.append(border)
    tblPr.append(tblBorders)

    # Set cell background colour
    cell = table.rows[0].cells[0]
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()

    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  colour)
    tcPr.append(shd)

    # Set cell height
    tr    = table.rows[0]._tr
    trPr  = OxmlElement("w:trPr")
    trH   = OxmlElement("w:trHeight")
    # Convert cm to twips (1 cm = 567 twips)
    twips = str(int(height_cm * 567))
    trH.set(qn("w:val"),      twips)
    trH.set(qn("w:hRule"),    "exact")
    trPr.append(trH)
    tr.insert(0, trPr)

    # Remove padding inside the cell so it looks like a solid bar
    cell.paragraphs[0].paragraph_format.space_before = Pt(0)
    cell.paragraphs[0].paragraph_format.space_after  = Pt(0)

    # Remove the default space Word adds BEFORE a table
    # This eliminates the visual gap that looks like a duplicate line
    tblPr2 = tbl.find(qn("w:tblPr"))
    tblLook = OxmlElement("w:tblLook")
    tblLook.set(qn("w:noHBand"), "1")
    if tblPr2 is not None:
        tblPr2.append(tblLook)
    # Set paragraph spacing before the table to zero
    p_before = OxmlElement("w:spacing")
    p_before.set(qn("w:before"), "0")
    p_before.set(qn("w:after"), "0")
    para_pr = cell.paragraphs[0]._p.get_or_add_pPr()
    para_pr.append(p_before)


def _extract_cover_meta(schema: dict, doc_type: str) -> dict:
    """
    Extracts meta information for the cover page bottom block.

    BRD: Version, Date, Author, Status (from document_control)
         Uses history[-1] = the LATEST version entry.

    MoM: Date, Time, Location, Facilitator (from meeting_info)
    """
    result = {}

    if doc_type == "BRD":
        ctrl = schema.get("document_control", {})
        if isinstance(ctrl, dict):

            # --- Version & Date from version_history ---
            history = ctrl.get("version_history", [])
            if history and isinstance(history[-1], dict):
                latest = history[-1]
                # girl 3 sometimes uses 'version', sometimes infers it from 'changes'
                raw_version = latest.get("version") or latest.get("ver")
                if raw_version:
                    result["Version"] = str(raw_version)
                else:
                    # Try to parse "version X.X" from the changes description
                    changes_text = str(latest.get("changes", ""))
                    import re
                    m = re.search(r"version\s*(\d+\.\d+)", changes_text, re.IGNORECASE)
                    result["Version"] = m.group(1) if m else "1.0"
                result["Date"] = latest.get("date", str(date.today()))

            # --- Author: handle both list-of-dicts AND list-of-strings ---
            authors = ctrl.get("authors", [])
            if authors:
                first = authors[0]
                if isinstance(first, dict):
                    result["Author"] = first.get("name", "")
                elif isinstance(first, str):
                    result["Author"] = first   # girl 3 sent plain strings

            # --- Status from approval ---
            approval = ctrl.get("approval", [])
            if approval and isinstance(approval[0], dict):
                raw = approval[0].get("status", "")
                result["Status"] = STATUS_LABELS.get(raw.lower(), raw.title())

        if not result:
            result["Date"] = str(date.today())

    elif doc_type == "MOM":
        info   = schema.get("meeting_info", {})
        source = info if isinstance(info, dict) else schema
        for label, keys in [
            ("Date",        ["date", "meeting_date"]),
            ("Time",        ["time", "meeting_time"]),
            ("Location",    ["location", "venue"]),
            ("Facilitator", ["facilitator", "chair", "host", "organizer"]),
        ]:
            for key in keys:
                val = source.get(key)
                if isinstance(val, str) and val.strip():
                    result[label] = val.strip()
                    break
        if not result:
            result["Date"] = str(date.today())

    return result


def _detect_doc_title(doc_type: str) -> str:
    """Returns the full document type title string."""
    titles = {
        "BRD": "Business Requirements Document",
        "MOM": "Minutes of Meeting",
        "SRS": "Software Requirements Specification",
    }
    return titles.get(doc_type, "Generated Document")


def _detect_project_name(schema: dict, doc_type: str) -> str:
    """
    Extracts a short name for the cover page large title.
    Avoids long sentences — splits at first comma, " is ", or ".".
    """
    search_keys = (
        ["meeting_title", "project_name", "title"]
        if doc_type == "MOM"
        else ["project_name", "company_name", "system_name", "title"]
    )
    for key in search_keys:
        val = schema.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    nested_key = "meeting_info" if doc_type == "MOM" else "executive_summary"
    nested = schema.get(nested_key, {})
    if isinstance(nested, dict):
        for key in ["meeting_title", "project_name", "company_name", "title"]:
            val = nested.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

        desc = nested.get("company_description", "")
        if isinstance(desc, str) and desc.strip():
            for sep in (" is ", " are ", ",", "."):
                if sep in desc:
                    candidate = desc.split(sep)[0].strip()
                    if len(candidate) < 30:
                        return candidate

    return ""


# -------------------------------------------------------------------
# PAGE LAYOUT
# -------------------------------------------------------------------

def _set_margins(doc: Document) -> None:
    """Sets 1-inch top/bottom and 1.25-inch left/right margins."""
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.25)
        section.right_margin  = Inches(1.25)


def _apply_styles(doc: Document) -> None:
    """Sets Calibri font, sizes, colours for all built-in styles."""
    s = doc.styles

    normal = s["Normal"]
    normal.font.name      = "Calibri"
    normal.font.size      = Pt(11)
    normal.font.color.rgb = BLACK
    normal.paragraph_format.space_after  = Pt(6)
    normal.paragraph_format.line_spacing = Pt(14)

    h1 = s["Heading 1"]
    h1.font.name      = "Calibri"
    h1.font.size      = Pt(14)
    h1.font.bold      = True
    h1.font.color.rgb = BLUE
    h1.paragraph_format.space_before   = Pt(16)
    h1.paragraph_format.space_after    = Pt(4)
    h1.paragraph_format.keep_with_next = True

    h2 = s["Heading 2"]
    h2.font.name      = "Calibri"
    h2.font.size      = Pt(12)
    h2.font.bold      = True
    h2.font.italic    = False
    h2.font.color.rgb = GREY
    h2.paragraph_format.space_before   = Pt(10)
    h2.paragraph_format.space_after    = Pt(2)
    h2.paragraph_format.keep_with_next = True

    try:
        s["List Bullet"].font.name = "Calibri"
        s["List Bullet"].font.size = Pt(11)
    except KeyError:
        pass


def _add_footer(doc: Document) -> None:
    """Adds centred 'Page X of Y' footer using Word field codes."""
    footer = doc.sections[0].footer
    para   = footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.clear()

    def _insert_field(run, field_name: str) -> None:
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        run._r.append(begin)
        instr = OxmlElement("w:instrText")
        instr.text = field_name
        run._r.append(instr)
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.append(end)

    for text, is_field, field_name in [
        ("Page ", False, None),
        ("",      True,  "PAGE"),
        (" of ",  False, None),
        ("",      True,  "NUMPAGES"),
    ]:
        r = para.add_run(text)
        r.font.size = Pt(9)
        if is_field:
            _insert_field(r, field_name)


def _add_bottom_border(paragraph, colour: str = "2E75B6") -> None:
    """
    Adds a thin bottom border under a paragraph.
    Used as the short decorative line under the project name.
    """
    pPr  = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "12")
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), colour)
    pBdr.append(bot)
    pPr.append(pBdr)