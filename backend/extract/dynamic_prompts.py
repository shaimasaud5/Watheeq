import json


def build_dynamic_prompt(template, transcript, doc_type):
    common_rules = """
Return ONLY valid JSON.
Do not write markdown.
Do not write explanations.
Do not add comments.
Do not invent unsupported facts.

IMPORTANT:
- The uploaded file is a document template, not the final answer.
- First infer the expected structure from the template content.
- Then extract matching information from the transcript.
- Keep the output aligned with the template's sections and field intent as closely as possible.
- If some information is missing, leave it empty rather than inventing values.
- Use consistent JSON formatting.

CRITICAL RULES:
- Use clean and meaningful JSON keys only.
- Do NOT generate malformed or broken keys like symbols or random characters.
- Do NOT mix fields between sections.
- Lists should contain only relevant fields.
- Each section must strictly follow its intended meaning.
"""

    brd_extra = """
This uploaded template is for a BRD-style document.
Focus on extracting structured business analysis information.
Possible sections may include business need, scope, requirements, stakeholders, risks, assumptions, dependencies, or approvals.
Preserve business-document style structure as much as possible.
"""

    mom_extra = """
This uploaded template is for a MOM-style document.
Focus on extracting meeting information such as meeting details, attendees, discussion points, decisions, action items, and next steps.
Preserve meeting-document style structure as much as possible.
"""

    if doc_type == "BRD":
        extra = brd_extra
    elif doc_type == "MOM":
        extra = mom_extra
    else:
        extra = ""

    return f"""
You are a structured information extraction engine.

Your task is to analyze the provided document template and understand its intended structure.
Then extract relevant information from the transcript and return a JSON output that follows that structure as closely as possible.

{common_rules}

{extra}

Uploaded document template content:
\"\"\"{template}\"\"\"

Transcript:
\"\"\"{transcript}\"\"\"

Return ONLY clean, valid, well-structured JSON without any malformed keys.
""".strip()