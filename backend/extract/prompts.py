import json


def build_brd_prompt(template, transcript):
    """
    Build the BRD extraction prompt for the LLM.
    """
    prompt = f"""
You are a BRD extraction engine.

Extract structured Business Requirements Document (BRD) data
from the transcript and fill the JSON template.

Return ONLY valid JSON.
Do not add extra keys.
Do not remove keys.
Do not write explanations.

RULES:
- Use only information from the transcript.
- If information is missing:
  - use not mentioned for single values
  - use [not mentioned] for lists
- Keep the same structure and data types as the template.
- need_for_change must be a descriptive sentence, not true/false.

GUIDELINES:

DOCUMENT CONTROL:
- If version numbers (e.g., 1.0, 1.1) are found, do not put them in date.
- Extract actual dates if available; otherwise leave date null.

EXECUTIVE SUMMARY:
Extract:
- company_description
- problem
- proposed_solution
- expected_benefits

BUSINESS DRIVERS:
Extract:
- need_for_change
- goals
- kpis

PROJECT SCOPE:
Extract:
- in_scope
- out_of_scope
- assumptions
- constraints

CURRENT PROCESS:
Extract:
- overview

RISK ANALYSIS:
Extract real risks only.
If impact or likelihood is mentioned (e.g., high, medium, low), extract them.

FUNCTIONAL REQUIREMENTS:
Extract system features mentioned in the transcript such as actions, capabilities, or user functions.

If the transcript includes phrases like "functional requirements include", "ability to", "system should", or descriptions of features, treat them as functional requirements.

NON-FUNCTIONAL REQUIREMENTS:
Extract performance, security, and usability requirements if mentioned such as speed, authentication, encryption, or user interface.

STAKEHOLDERS:
Extract name, role, responsibility if mentioned.

REFERENCES:
Extract documents if mentioned.

Template:
{json.dumps(template, ensure_ascii=False)}

Transcript:
\"\"\"{transcript}\"\"\"

Return ONLY JSON.
""".strip()
    return prompt
