# def build_mom_extraction_prompt(transcript: str, schema_text: str) -> str:
#     return f"""
# You are an expert business analyst and meeting documentation assistant.

# Your task is to extract structured Minutes of Meeting (MOM) information from the following meeting transcript.

# Return ONLY valid JSON.
# The JSON must strictly follow the provided schema structure.
# Do not include markdown.
# Do not add explanations.

# General Rules:
# 1. Extract as much relevant information as possible from the transcript.
# 2. Do NOT invent information that is not supported by the text.
# 3. If information is missing, use "Not Mentioned" for string fields.
# 4. If a list has no data, return an empty list [].
# 5. Maintain proper JSON structure (objects must not be replaced with plain strings).

# Participants Rules:
# - Participants must be objects with:
#   - name
#   - role
# - If role is not mentioned, set it to "Not Mentioned".
# - Do not infer roles from context (e.g., "led the meeting" ≠ "Leader").

# Discussion Rules:
# - Extract only key discussion topics.
# - Keep summaries concise and meaningful.

# Action Items Rules:
# - Only include tasks that are clearly assigned or implied as actionable.
# - Each action item must include:
#   - task
#   - assigned_to
#   - deadline
#   - priority
#   - status
# - If any field is missing, set it to "Not Mentioned".

# Decision Rules:
# - Include only confirmed decisions.
# - Each decision must include:
#   - decision
#   - impact ("Not Mentioned" if unclear)

# Follow-up Meeting Rules:
# - If a future meeting is mentioned (e.g., "next week", "follow-up meeting"):
#   - required = true
#   - extract date and purpose if available
# - Otherwise:
#   - required = false
#   - proposed_date = "Not Mentioned"
#   - purpose = "Not Mentioned"

# Supporting Documents Rules:
# - Include documents only if explicitly mentioned (e.g., report, sheet, document).

# Important:
# - Do NOT return empty objects .
# - Try to extract meaningful values whenever possible.
# - Prefer extracting partial information rather than leaving fields empty.


# Schema:
# {schema_text}

# Transcript:
# {transcript}
# """.strip()

def build_mom_extraction_prompt(transcript: str, schema_text: str) -> str:
    return f"""
You are an expert Minutes of Meeting (MOM) extractor.

Return ONLY valid JSON that matches the schema.

Schema:
{schema_text}

Example:

Transcript:
"The meeting started at 10 AM. Ahmed presented the timeline. Sarah will update the budget by Monday. The team decided to delay phase two."

Output:
{{
  "meeting_details": {{
    "project_name": "Not Mentioned",
    "meeting_title": "Meeting",
    "date": "Not Mentioned",
    "start_time": "10 AM",
    "end_time": "Not Mentioned",
    "location_or_platform": "Not Mentioned"
  }},
  "attendees": {{
    "participants": [
      {{"name": "Ahmed", "role": "Not Mentioned"}},
      {{"name": "Sarah", "role": "Not Mentioned"}}
    ],
    "absentees": []
  }},
  "agenda_and_objectives": {{
    "agenda": [],
    "meeting_objectives": []
  }},
  "discussion_points": [
    {{
      "topic": "timeline",
      "summary": "Ahmed presented the timeline",
      "key_points": []
    }}
  ],
  "action_items": [
    {{
      "task": "update the budget",
      "assigned_to": "Sarah",
      "deadline": "Monday",
      "priority": "Not Mentioned",
      "status": "Not Mentioned"
    }}
  ],
  "key_decisions": [
    {{
      "decision": "delay phase two",
      "impact": "Not Mentioned"
    }}
  ],
  "follow_up_items": {{
    "next_steps": [],
    "future_meeting": {{
      "required": false,
      "proposed_date": "Not Mentioned",
      "purpose": "Not Mentioned"
    }}
  }},
  "additional_notes": [],
  "supporting_documents": []
}}

Now extract from this transcript:

{transcript}
""".strip()