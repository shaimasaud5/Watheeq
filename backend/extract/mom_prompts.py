def build_mom_extraction_prompt(transcript: str, schema_text: str) -> str:
    return f"""
You are an expert business analyst and meeting documentation assistant.

Your task is to extract structured Minutes of Meeting (MOM) information from the following meeting transcript.

Return ONLY valid JSON.
The JSON must strictly match the provided schema structure.
Do not include markdown.
Do not add explanations.
Do not invent information.
If a field is not explicitly mentioned in the transcript, return an empty string, empty array, empty object, or false where appropriate.

Important extraction rules:
1. Extract only information that is clearly stated or strongly supported by the transcript.
2. Do not hallucinate names, roles, decisions, deadlines, or action items.
3. Do not convert general discussion into action items unless a clear task or responsibility is mentioned.
4. Do not convert suggestions into decisions unless a final decision is clearly made.
5. Keep discussion_points focused on major topics only.
6. Keep action_items specific and actionable.
7. Keep key_decisions limited to confirmed decisions.
8. If no future meeting is mentioned, set:
   "required": false,
   "proposed_date": "",
   "purpose": ""
9. Supporting documents should only include documents explicitly referenced in the transcript.

Schema:
{schema_text}

Transcript:
{transcript}
""".strip()