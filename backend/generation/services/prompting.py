# generation/services/prompting.py
# ----------------------------------
# This file has two jobs:
#   1. Build the prompts we send to the LLM (one per schema field)
#   2. Define helper functions used by orchestrator and renderer
#
# PROMPT STRATEGY:
#   Two separate prompts — one for BRD, one for MoM.
#   Each is grounded in a recognised international standard:
#
#   BRD → ISO/IEC/IEEE 29148:2018
#         "Systems and software engineering — Life cycle processes —
#          Requirements engineering"
#         Governs: unambiguity, completeness, singularity, verifiability,
#         traceability — the five quality criteria for requirements text.
#
#   MoM → ISO 15489-1:2016  (Records Management)
#         "Information and documentation — Records management"
#         Governs: accuracy, completeness, reliability, authenticity of
#         meeting records. Combined with Robert's Rules of Order for
#         decision and action-item language.
#
# SHAPE-BASED DISPATCH PHILOSOPHY (unchanged):
#   We do NOT hardcode field names anywhere in this file.
#   Every decision is made by inspecting the VALUE'S SHAPE:
#
#     dict OR list  → should_skip_llm() = True  (renderer handles)
#     string        → should_skip_llm() = False (LLM writes prose)

from typing import Any


# -------------------------------------------------------------------
# ACRONYMS
# -------------------------------------------------------------------
_ACRONYMS = {
    "kpis":  "KPIs",
    "kpi":   "KPI",
    "id":    "ID",
    "brd":   "BRD",
    "mom":   "MoM",
    "srs":   "SRS",
    "ui":    "UI",
    "ux":    "UX",
    "api":   "API",
    "url":   "URL",
    "aov":   "AOV",
    "ai":    "AI",
    "it":    "IT",
    "hr":    "HR",
}

# -------------------------------------------------------------------
# SKIP_LLM_FIELDS
# -------------------------------------------------------------------
SKIP_LLM_FIELDS = {
    "document_control",   # always a nested dict: authors, approval, version_history
    "meeting_info",       # always a nested dict: date, time, location, facilitator
}

# Token budget — single fixed value.
# Sentence count in the prompt controls output length.
TOKEN_LIMIT = 600


# -------------------------------------------------------------------
# SHAPE DETECTION
# -------------------------------------------------------------------

def is_list_of_dicts(value: Any) -> bool:
    """True if value is a non-empty list where every item is a dict."""
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(item, dict) for item in value)
    )


def is_structural(value: Any) -> bool:
    """
    True if the value's shape means the LLM should be skipped entirely.
    Structural = dict OR any non-empty list (of dicts OR of strings).
    """
    if isinstance(value, dict):
        return True
    if isinstance(value, list) and len(value) > 0:
        return True
    return False


def should_skip_llm(field_key: str, field_value: Any) -> bool:
    """
    Decides whether to skip the LLM for this field.
    Shape-based — no hardcoded field name lists beyond SKIP_LLM_FIELDS.
    """
    if field_key in SKIP_LLM_FIELDS:
        return True
    return is_structural(field_value)


def get_token_limit(field_key: str) -> int:
    """Returns the token budget for any field."""
    return TOKEN_LIMIT


# -------------------------------------------------------------------
# LABEL AND TEXT HELPERS
# -------------------------------------------------------------------

def key_to_label(key: str) -> str:
    """
    Converts a snake_case key into a readable title.
    Examples:
        "executive_summary"           -> "Executive Summary"
        "non_functional_requirements" -> "Non Functional Requirements"
        "kpis"                        -> "KPIs"
    """
    words = key.split("_")
    result = []
    for word in words:
        lower = word.lower()
        result.append(_ACRONYMS[lower] if lower in _ACRONYMS else word.capitalize())
    return " ".join(result)


def value_to_raw_text(value: Any) -> str:
    """
    Flattens any JSON value into a single plain-English string.
    Used to feed context to the LLM for prose fields.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(", ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if isinstance(v, list):
                parts.append(f"{k}: {', '.join(str(i) for i in v)}")
            elif isinstance(v, dict):
                parts.append(f"{k}: {', '.join(str(x) for x in v.values())}")
            else:
                parts.append(f"{k}: {v}")
        return "; ".join(parts)
    return str(value)


# ===================================================================
# BRD PROMPT
# Standard: ISO/IEC/IEEE 29148:2018 — Requirements Engineering
# ===================================================================

_BRD_ISO_BLOCK = """
QUALITY STANDARD — ISO/IEC/IEEE 29148:2018 (Requirements Engineering):
Every sentence you write must satisfy ALL five criteria:

1. UNAMBIGUOUS — one and only one interpretation.
   Avoid: "fast", "efficient", "user-friendly", "reliable", "easy", "good"
   Use instead: measurable values, specific conditions, named actors.
   Wrong:  "The system shall respond quickly."
   Correct: "The system shall respond within 2 seconds for 95% of requests
             under a concurrent load of 500 users."

2. COMPLETE — state WHO does WHAT, under WHAT CONDITIONS, with WHAT OUTCOME.
   Do not leave the reader needing additional context to understand the statement.

3. SINGULAR — one capability, constraint, or quality per sentence.
   Wrong:  "Users can register, log in, and manage their profile."
   Correct: "Users shall register using a verified mobile number via OTP."

4. VERIFIABLE — every claim must be objectively testable or measurable.
   Preserve all numbers, thresholds, and percentages from the DATA exactly.
   If no numbers are given, describe outcomes in observable, testable terms.

5. TRACEABLE — every statement must originate directly from the DATA provided.
   Do NOT add assumptions, domain knowledge, or facts not present in the DATA.
""".strip()

_BRD_FEW_SHOT = """
EXAMPLE 1 — business objective:
SECTION: Need For Change
DATA: Lack of personalised engagement, outdated reporting dashboards causing 23% drop in retention
OUTPUT: The absence of personalised customer engagement mechanisms and reliance on outdated reporting dashboards have contributed to a documented 23% decline in customer retention, necessitating a fundamental transformation of the analytics and engagement infrastructure.

EXAMPLE 2 — proposed solution:
SECTION: Proposed Solution
DATA: Centralised analytics platform with automated customer segmentation and real-time dashboards
OUTPUT: The proposed solution is a centralised analytics platform that automates customer segmentation based on behavioural data and delivers real-time performance dashboards accessible to authorised stakeholders across all business units.

EXAMPLE 3 — functional requirement with priority:
SECTION: Functional Requirements
DATA: priority: must-have; description: system must handle 10,000 concurrent users without response degradation
OUTPUT: A high-priority functional requirement mandates that the system sustain a minimum of 10,000 concurrent user sessions without measurable degradation in response time, as defined by a maximum threshold of 3 seconds per transaction under full load.

EXAMPLE 4 — scope statement:
SECTION: Project Scope
DATA: In scope: web dashboard, CRM integration. Out of scope: mobile app, ERP redesign.
OUTPUT: The project scope encompasses the development of a web-based analytics dashboard and its integration with the existing CRM system. The development of a mobile application and any redesign of the legacy ERP system fall explicitly outside the defined project boundaries.

EXAMPLE 5 — BAD vs GOOD:
DATA: The platform must support Arabic and English.
BAD:  Here is the language section: The platform supports Arabic and English languages.
GOOD: The platform shall support both Arabic and English languages, with full Unicode compliance, enabling seamless language switching for all authenticated users.
""".strip()

_BRD_STRICT_RULES = """
STRICT OUTPUT RULES:
1. Output ONLY the sentences — no title, no label, no preamble, no closing remark.
2. Do NOT start with: "Here is", "Sure", "Certainly", "This section", "Based on",
   "The following", "I will", "As requested", or any similar phrase.
3. Do NOT include any information not present in the DATA above.
4. Do NOT use bullet points, numbered lists, or dashes — continuous prose only.
5. Write in formal business English throughout.
6. Do NOT repeat the section name in your output.
7. End with a period.
8. Priority levels MUST be expressed as "High", "Medium", or "Low" only.
   NEVER use MoSCoW terms (must, should, could, won't) as priority labels.
""".strip()


# ===================================================================
# MoM PROMPT
# Standards: ISO 15489-1:2016 (Records Management) +
#            Robert's Rules of Order (meeting procedure)
# ===================================================================

_MOM_STANDARDS_BLOCK = """
QUALITY STANDARD — ISO 15489-1:2016 (Records Management) &
                   Robert's Rules of Order (Meeting Procedure):

ISO 15489-1:2016 requires meeting records to be:
  ACCURATE   — reflect exactly what was discussed, decided, and assigned.
               Do not embellish, interpret, or add context beyond the DATA.
  COMPLETE   — cover all key points: context, discussion points, conclusions.
  RELIABLE   — use precise, unambiguous language so the record is trustworthy
               as an official organisational document.
  AUTHENTIC  — use past tense for discussions and decisions already made.
               Use present tense only for standing agreements or policies.

Robert's Rules of Order requires:
  DECISIONS  — state the outcome clearly: what was resolved, by whom, effective when.
  ACTION ITEMS — state the task, the responsible party, and the deadline explicitly.
  DISCUSSION — summarise the substance of debate, not the speakers' identities
               unless attribution is specifically relevant.
""".strip()

_MOM_FEW_SHOT = """
EXAMPLE 1 — discussion summary:
SECTION: Discussion Summary
DATA: Omar presented business case for redesigning platform, highlighted 23% drop in mobile conversion. Walid confirmed client expects go-live before Ramadan 2027. Saud raised concerns about 6-month timeline feasibility for product catalog migration.
OUTPUT: The session opened with a presentation of the business case for platform redesign, which identified a 23% decline in mobile conversion rates as the primary driver. The client representative confirmed that deployment must be completed prior to the Ramadan 2027 sales period. The technical lead raised concerns regarding the feasibility of completing the product catalogue migration within the proposed six-month timeline, citing the volume and complexity of existing catalogue data as primary risk factors.

EXAMPLE 2 — decision:
SECTION: Decisions
DATA: Phased delivery adopted: Phase 1 by August 2026, Phase 2 by December 2026. Weekly meetings every Tuesday 10 AM.
OUTPUT: The team resolved to adopt a phased delivery approach, with Phase 1 scheduled for completion by August 2026 and Phase 2 by December 2026. It was further agreed that weekly progress meetings would be held every Tuesday at 10:00 AM for the duration of the project.

EXAMPLE 3 — next steps:
SECTION: Next Meeting
DATA: March 25 2026 at 10:00 AM — scope clarification session
OUTPUT: The subsequent meeting is scheduled for 25 March 2026 at 10:00 AM and will focus on clarifying outstanding scope boundaries in preparation for finalising the requirements document.

EXAMPLE 4 — notes:
SECTION: Notes
DATA: Walid requested deliverables via client portal not email. Saud flagged DevOps dependency affecting Phase 1 timeline.
OUTPUT: The client representative requested that all project deliverables be shared exclusively through the designated client portal rather than via email correspondence. The technical lead identified a dependency on DevOps team availability as a potential risk to the Phase 1 delivery timeline.

EXAMPLE 5 — BAD vs GOOD:
DATA: The team discussed the budget and agreed it needed review.
BAD:  Here is a summary of the budget discussion.
GOOD: The allocated budget was reviewed by the team, and a consensus was reached that a formal reassessment of the financial plan is required before proceeding to the next project phase.
""".strip()

_MOM_STRICT_RULES = """
STRICT OUTPUT RULES:
1. Output ONLY the sentences — no title, no label, no preamble, no closing remark.
2. Do NOT start with: "Here is", "Sure", "Certainly", "This section", "Based on",
   "The following", or any similar introduction phrase.
3. Do NOT include any information not present in the DATA above.
4. Do NOT use bullet points, numbered lists, or dashes — continuous prose only.
5. Use past tense for discussions and decisions (they have already occurred).
6. Use formal business English throughout.
7. Do NOT repeat the section name in your output.
8. End with a period.
""".strip()


# ===================================================================
# PUBLIC PROMPT BUILDER
# ===================================================================

def build_field_prompt(field_key: str, field_value: Any, doc_type: str = "BRD") -> str:
    """
    Builds ONE prose-expansion prompt for ONE schema field.

    Called ONLY when should_skip_llm() returned False —
    meaning the value is a string or a simple list of strings.

    Parameters:
        field_key   - snake_case key from the schema (e.g. "executive_summary")
        field_value - the raw value from the schema
        doc_type    - "BRD" or "MOM" — selects the correct prompt template
                      and international standard. Defaults to "BRD".

    The LLM decides how many sentences to write based on the DATA itself.
    This keeps the function fully schema-agnostic — no field names, no counts.
    """
    label    = key_to_label(field_key)
    raw_text = value_to_raw_text(field_value)

    if doc_type == "MOM":
        return _build_mom_prompt(label, raw_text)

    # Default: BRD (also used for SRS if added later)
    return _build_brd_prompt(label, raw_text)


def _build_brd_prompt(label: str, raw_text: str) -> str:
    """
    BRD prompt grounded in ISO/IEC/IEEE 29148:2018.
    Persona: senior business analyst writing a formal requirements document.
    """
    return f"""You are a senior business analyst authoring a formal Business Requirements Document (BRD).
Your writing must conform to ISO/IEC/IEEE 29148:2018 — the international standard for requirements engineering.

{_BRD_ISO_BLOCK}

Study these examples of correct output style:

{_BRD_FEW_SHOT}

---
Now write the section below, applying the ISO 29148 quality criteria and matching the example style exactly.

SECTION: {label}
DATA: {raw_text}

Write as many sentences as needed to cover all the DATA above — no more, no less.

{_BRD_STRICT_RULES}

OUTPUT:"""


def _build_mom_prompt(label: str, raw_text: str) -> str:
    """
    MoM prompt grounded in ISO 15489-1:2016 and Robert's Rules of Order.
    Persona: professional minute-taker producing an official meeting record.
    """
    return f"""You are a professional minute-taker producing an official Minutes of Meeting (MoM) record.
Your writing must conform to ISO 15489-1:2016 (Records Management) and follow Robert's Rules of Order for meeting procedure language.

{_MOM_STANDARDS_BLOCK}

Study these examples of correct output style:

{_MOM_FEW_SHOT}

---
Now write the section below, applying the records management standards and matching the example style exactly.

SECTION: {label}
DATA: {raw_text}

Write as many sentences as needed to cover all the DATA above — no more, no less.

{_MOM_STRICT_RULES}

OUTPUT:"""