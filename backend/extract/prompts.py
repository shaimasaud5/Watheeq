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

#     prompt = f"""
# You are a strict BRD information extraction engine.

# Your task is to extract Business Requirements Document (BRD) information from the transcript
# and fill the target JSON template.

# Return ONLY valid JSON.
# Do not write markdown.
# Do not write explanations.
# Do not add comments.
# Do not add extra keys.
# Do not remove keys.
# Do not change the JSON structure.
# Follow the template structure exactly.

# GENERAL RULES:
# - Extract information ONLY from the transcript.
# - Do not invent or assume facts that are not supported by the transcript.
# - Do not convert prompt instructions into output.
# - Preserve the same nesting and field names as the template.
# - Keep the same data type as the template for every field.

# TYPE RULES:
# - If a field is a list in the template, return a list.
# - If a field is an object in the template, return an object.
# - If a field is a scalar field, return a string or null.
# - Never replace a list with a string.
# - Never replace an object with a string.

# MISSING DATA RULES:
# - If information is missing:
#   - use null for scalar/object fields
#   - use [] for array fields
# - Do not create fake entries with all null values.

# CLASSIFICATION RULES:
# - Put information in the most appropriate section only.
# - Do NOT classify everything as risk.
# - Do NOT place general business goals inside risk_analysis.
# - Do NOT place functional requirements inside non_functional_requirements.

# Here is the target JSON template:
# {json.dumps(template, ensure_ascii=False)}

# Now extract from this transcript:

# Transcript:
# \"\"\"{transcript}\"\"\"

# Return ONLY the filled JSON.
# """.strip()

#     return prompt
