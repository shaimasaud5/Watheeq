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