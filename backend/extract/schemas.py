# extract/schemas.py
# ───────────────────
# Static schemas for BRD and MOM documents.
# The Extraction stage fills these schemas using
# information extracted from the transcript.
# The Generation stage then uses the filled schemas to generate the final .docx document.

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
   "functional_requirements": [
        {
         "priority": None,
         "description": None,
        }
    ],
    "non_functional_requirements": {
        "performance": [],
        "security": [],
        "usability": [],
    },
    "risk_analysis": [
        {
            "description": None,
            "impact": None,
        "   probability": None,
        }
    ],
    "document_control": {
        "authors": [],
        "approval": [],
        "version_history": [],
    },
    "glossary": [
     {
         "term": None,
         "definition": None,
     }
    ],
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
    "attendees": [
     {
        "name": None,
        "role": None,
        }
    ],
    "agenda": [],
    "discussion_summary": None,
    "decisions": [],
    "action_items": [
        {
          "task": None,
         "owner": None,
         "due_date": None,
         "status": None,
        }
    ],
    "next_meeting": None,
    "notes": None,
}
