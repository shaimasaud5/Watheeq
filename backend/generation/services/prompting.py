# generation/services/prompting.py
# ──────────────────────────────────
# prompt واحد كبير يرسل السكيما كاملة للنموذج دفعة واحدة.
# يتضمن معايير ISO + أمثلة few-shot + قواعد صارمة.

from typing import Any


def key_to_label(key: str) -> str:
    """يحوّل snake_case إلى عنوان قابل للقراءة."""
    acronyms = {
        "kpis": "KPIs", "kpi": "KPI", "id": "ID",
        "brd": "BRD", "mom": "MoM", "api": "API",
        "ui": "UI", "ux": "UX", "url": "URL", "ai": "AI",
    }
    words = key.split("_")
    return " ".join(acronyms.get(w.lower(), w.capitalize()) for w in words)


# ═══════════════════════════════════════════════════════════════
# BRD — معايير ISO + أمثلة + قواعد
# ═══════════════════════════════════════════════════════════════

_BRD_ISO_BLOCK = """
QUALITY STANDARD — ISO/IEC/IEEE 29148:2018 (Requirements Engineering):
Every sentence you write must satisfy ALL of these criteria:

1. UNAMBIGUOUS — one and only one interpretation.
   Avoid vague words: "fast", "efficient", "user-friendly", "reliable", "easy", "good".
   Use measurable values and specific conditions instead.
   Wrong:  "The system shall respond quickly."
   Correct: "The system shall respond within 2 seconds for 95% of requests."

2. COMPLETE — state WHO does WHAT, under WHAT CONDITIONS, with WHAT OUTCOME.

3. SINGULAR — one capability or constraint per sentence.
   Wrong:  "Users can register, log in, and manage their profile."
   Correct: "Users shall register using a verified mobile number via OTP."

4. VERIFIABLE — every claim must be objectively testable or measurable.
   Preserve all numbers, thresholds, and percentages from the DATA exactly.

5. TRACEABLE — every statement must originate directly from the DATA provided.
   Do NOT add assumptions or facts not present in the DATA.
""".strip()

_BRD_FEW_SHOT = """
EXAMPLES OF CORRECT OUTPUT:

EXAMPLE 1 — problem statement:
DATA: current system is slow and has errors in requests
OUTPUT: The existing order management system exhibits critical performance deficiencies, including processing delays and a measurable error rate in request handling, both of which are adversely affecting operational efficiency and customer satisfaction.

EXAMPLE 2 — proposed solution:
DATA: new system supporting Order Tracking and Inventory Management
OUTPUT: The proposed solution is a centralised system that provides real-time Order Tracking and automated Inventory Management, designed to eliminate the processing errors and delays identified in the current system.

EXAMPLE 3 — functional requirement:
DATA: priority: High, description: system must allow users to track orders
OUTPUT: Title: Order Tracking
Priority: High
Description: The system shall enable authenticated users to track the real-time status of any submitted order, with status updates reflected within 30 seconds of any change occurring in the fulfilment pipeline.

EXAMPLE 4 — scope statement:
DATA: in scope: Order Tracking, Dashboard. out of scope: Mobile App
OUTPUT: In Scope:
- Order Tracking will be developed as a core module, enabling users to monitor order status in real time.
- A centralised Dashboard will be developed to provide management with a unified view of system activity.
Out of Scope:
- A mobile application falls outside the boundaries of this project and will not be developed.

EXAMPLE 5 — BAD vs GOOD:
DATA: the system must be secure
BAD:  The system should be secure and protect user data.
GOOD: The system shall enforce role-based access control, requiring multi-factor authentication for all administrative users, and shall encrypt all data at rest and in transit using AES-256.
""".strip()

_BRD_STRICT_RULES = """
STRICT OUTPUT RULES:
1. Output ONLY the section content — no title, no preamble, no closing remark.
2. Do NOT start with: "Here is", "Sure", "Certainly", "This section", "Based on", or similar.
3. Do NOT include information not present in the SCHEMA DATA above.
4. For TEXT fields: write in continuous prose — no bullet points.
5. For LIST fields: each item starts with "- " on its own line.
6. For ITEM fields: use the exact format shown (Title/Priority/Description).
7. Priority values must be: High, Medium, or Low ONLY.
8. Write in formal business English throughout.
9. End every prose section with a period.
""".strip()


# ═══════════════════════════════════════════════════════════════
# MOM — معايير ISO + أمثلة + قواعد
# ═══════════════════════════════════════════════════════════════

_MOM_ISO_BLOCK = """
QUALITY STANDARD — ISO 15489-1:2016 (Records Management) & Robert's Rules of Order:

ISO 15489-1:2016 requires meeting records to be:
  ACCURATE   — reflect exactly what was discussed and decided. Do not embellish.
  COMPLETE   — cover all key points: context, discussion, conclusions.
  RELIABLE   — use precise, unambiguous language as an official organisational document.
  AUTHENTIC  — use past tense for discussions and decisions already made.

Robert's Rules of Order requires:
  DECISIONS    — state the outcome clearly: what was resolved, effective when.
  ACTION ITEMS — state the task, the responsible party, and the deadline explicitly.
  DISCUSSION   — summarise the substance of debate objectively.
""".strip()

_MOM_FEW_SHOT = """
EXAMPLES OF CORRECT OUTPUT:

EXAMPLE 1 — discussion summary:
DATA: team discussed redesigning platform, 23% drop in mobile conversion, client expects go-live before Ramadan 2027
OUTPUT: The session opened with a presentation of the business case for platform redesign, which identified a 23% decline in mobile conversion rates as the primary driver. The client representative confirmed that deployment must be completed prior to the Ramadan 2027 sales period.

EXAMPLE 2 — decision:
DATA: phased delivery adopted, Phase 1 by August 2026, weekly meetings every Tuesday 10 AM
OUTPUT: - The team resolved to adopt a phased delivery approach, with Phase 1 scheduled for completion by August 2026.
- It was agreed that weekly progress meetings would be held every Tuesday at 10:00 AM.

EXAMPLE 3 — action item:
DATA: task: prepare scope document, owner: Sara, due: May 15
OUTPUT: Task: Sara shall prepare and submit the project scope document for review by all stakeholders.
Owner: Sara
Due Date: May 15
Status: Open

EXAMPLE 4 — BAD vs GOOD:
DATA: team discussed budget and agreed it needed review
BAD:  The team talked about budget and said they need to review it.
GOOD: The allocated budget was reviewed by the team, and a consensus was reached that a formal reassessment of the financial plan is required before proceeding to the next project phase.
""".strip()

_MOM_STRICT_RULES = """
STRICT OUTPUT RULES:
1. Output ONLY the section content — no title, no preamble, no closing remark.
2. Do NOT start with: "Here is", "Sure", "Certainly", "This section", or similar.
3. Do NOT include information not present in the SCHEMA DATA above.
4. For TEXT fields: write in continuous prose — no bullet points.
5. For LIST fields: each item starts with "- " on its own line.
6. For ITEM fields: use the exact format shown (Task/Owner/Due Date/Status).
7. Use past tense for all discussions and decisions.
8. Write in formal business English throughout.
9. End every prose section with a period.
""".strip()


# ═══════════════════════════════════════════════════════════════
# الدوال الرئيسية
# ═══════════════════════════════════════════════════════════════

def build_brd_prompt(filled_schema: dict) -> str:
    """
    يبني prompt كامل لوثيقة BRD.
    يرسل السكيما كاملة مع معايير ISO وأمثلة few-shot.
    """
    import json
    schema_text = json.dumps(filled_schema, ensure_ascii=False, indent=2)

    return f"""You are a senior business analyst writing a complete, professional Business Requirements Document (BRD).

{_BRD_ISO_BLOCK}

{_BRD_FEW_SHOT}

---

SCHEMA DATA:
{schema_text}

---

INSTRUCTIONS:
Write ALL sections below in this exact order.
Skip a section ONLY if its data in the schema is completely empty or null.
If a field has no data, write "No [field name] is provided." — do NOT hallucinate.

OUTPUT FORMAT — use these exact tags:

[SECTION: executive_summary]
[FIELD: company_description]
Prose here (1-8 sentences).
[FIELD: problem]
Prose here.
[FIELD: proposed_solution]
Prose here.
[FIELD: expected_benefits]
- benefit one expanded to 1-3 sentences
- benefit two expanded

[SECTION: business_drivers]
[FIELD: need_for_change]
Prose here.
[FIELD: goals]
- goal one expanded
- goal two expanded
[FIELD: kpis]
- kpi one expanded

[SECTION: project_scope]
[FIELD: in_scope]
- component one (HIGH-LEVEL SYSTEM COMPONENTS only — not functional requirements)
- component two
[FIELD: out_of_scope]
- item one
[FIELD: assumptions]
- assumption one
[FIELD: constraints]
- constraint one

[SECTION: stakeholders]
- stakeholder role one expanded
- stakeholder role two expanded

[SECTION: current_process]
[FIELD: overview]
Prose here.
[FIELD: pain_points]
- pain point one expanded

[SECTION: functional_requirements]
[ITEM]
Title: <specific feature name>
Priority: <High, Medium, or Low>
Description: <1-3 sentences — specific and measurable>
---
[ITEM]
Title: <next feature>
Priority: <High, Medium, or Low>
Description: <1-3 sentences>
---

[SECTION: non_functional_requirements]
[FIELD: performance]
- performance requirement expanded
[FIELD: security]
- security requirement expanded
[FIELD: usability]
- usability requirement expanded

[SECTION: risk_analysis]
[ITEM]
Risk: <risk name>
Impact: <High, Medium, or Low>
Description: <1-3 sentences>
---

[SECTION: glossary]
[ITEM]
Term: <technical term>
Definition: <its meaning>
---

[SECTION: references]
- reference one
[SECTION: appendix]
- appendix item one

---

{_BRD_STRICT_RULES}

IMPORTANT — FUNCTIONAL REQUIREMENTS:
- Each [ITEM] must be ONE specific feature only — do NOT combine multiple features.
- Wrong: "Title: Order Tracking and Inventory Management"
- Correct: write two separate [ITEM] blocks.

Begin writing now:"""


def build_mom_prompt(filled_schema: dict) -> str:
    """
    يبني prompt كامل لوثيقة MOM.
    يرسل السكيما كاملة مع معايير ISO وأمثلة few-shot.
    """
    import json
    schema_text = json.dumps(filled_schema, ensure_ascii=False, indent=2)

    return f"""You are a professional minute-taker writing a complete, official Minutes of Meeting (MoM) document.

{_MOM_ISO_BLOCK}

{_MOM_FEW_SHOT}

---

SCHEMA DATA:
{schema_text}

---

INSTRUCTIONS:
Write ALL sections below in this exact order.
Skip a section ONLY if its data in the schema is completely empty or null.
Do NOT include meeting_info — it appears on the cover page only.

OUTPUT FORMAT — use these exact tags:

[SECTION: attendees]
- attendee name and role
- attendee name and role

[SECTION: agenda]
- agenda item one expanded
- agenda item two expanded

[SECTION: discussion_summary]
Prose here (past tense, 1-8 sentences).

[SECTION: decisions]
- decision one expanded (past tense)
- decision two expanded

[SECTION: action_items]
[ITEM]
Task: <task expanded 1-3 sentences>
Owner: <owner>
Due Date: <due date or "Not specified">
Status: <status or "Open">
---

[SECTION: next_meeting]
Prose here.

[SECTION: notes]
Prose here.

---

{_MOM_STRICT_RULES}

Begin writing now:"""