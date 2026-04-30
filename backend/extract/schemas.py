# extract/schemas.py
# ───────────────────
# السكيمات الثابتة لوثيقتي BRD و MOM.
# مهمة 3 تملأ هذي السكيمات من الترانسكريبت.
# مهمة 4 تستخدم النتيجة لتوليد الـ .docx

BRD_SCHEMA = {
    "executive_summary": {
        "company_description": None,
        "problem": None,
        "proposed_solution": None,
        "expected_benefits": [],
    },
    "business_drivers": {
        "need_for_change": None,
        "goals": [],
        "kpis": [],
    },
    "project_scope": {
        "in_scope": [],
        "out_of_scope": [],
        "assumptions": [],
        "constraints": [],
    },
    "stakeholders": [],
    "current_process": {
        "overview": None,
        "pain_points": [],
    },
    "functional_requirements": [],
    "non_functional_requirements": {
        "performance": [],
        "security": [],
        "usability": [],
    },
    "risk_analysis": [],
    "document_control": {
        "authors": [],
        "approval": [],
        "version_history": [],
    },
    "glossary": [],
    "references": [],
    "appendix": [],
}


MOM_SCHEMA = {
    "meeting_info": {
        "meeting_title": None,
        "date": None,
        "time": None,
        "location": None,
        "facilitator": None,
    },
    "attendees": [],
    "agenda": [],
    "discussion_summary": None,
    "decisions": [],
    "action_items": [],
    "next_meeting": None,
    "notes": None,
}
