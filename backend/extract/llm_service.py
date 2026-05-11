# extract/llm_service.py
# ───────────────────────
# Sends a prompt to the LLM to extract one schema section value.

import json
import re
import requests
from typing import Optional
import os
from groq import Groq


OLLAMA_URL = "http://ollama:11434/api/generate"
#MODEL_NAME = "llama3.2"
MODEL_NAME = "llama-3.3-70b-versatile"

def _call_ollama(prompt: str) -> Optional[str]:
    """Send the prompt to Groq and return the raw text response."""
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY_TASK3"))
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GROQ ERROR: {e}")
        return None


def _safe_parse(text: str) -> Optional[dict]:
    """Try to extract and parse JSON from the LLM response."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"(\{(?:.*\n?)*\})", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def extract_section(section_name: str, section_template, context: str, doc_type: str = "BRD") -> Optional[dict]:
    """
    Send the LLM the required extraction inputs:
    - section name
    - expected section structure (section_template)
    - top 5 transcript chunks as context

    The LLM is instructed to fill the section using only the provided context.
    Returns a dictionary matching the section_template structure.
    """
    template_str = json.dumps({section_name: section_template}, ensure_ascii=False, indent=2)

    if doc_type == "MOM":
        persona = "expert meeting minutes analyst extracting structured information from meeting transcripts"
        section_guidance = {
            "meeting_info": (
                "meeting_title: The topic or name of the meeting. "
                "date: The date the meeting took place. "
                "time: The time the meeting started. "
                "location: Physical location or platform (e.g. Zoom, Teams, in-person). "
                "facilitator: The person who led or chaired the meeting."
            ),
            "attendees": (
                "These are ONLY people who were PRESENT and SPEAKING in the meeting. "
                "Do NOT include people who were merely mentioned or discussed during the meeting. "
                "name: Full name if mentioned. "
                "role: Their job title or role in the organization."
            ),
            "agenda": (
                "The list of topics that were discussed in the meeting. "
                "Extract each topic as a separate agenda item. "
                "These should be high-level topics, not detailed discussions."
            ),
            "discussion_summary": (
                "A summary of what was discussed, debated, or reviewed in the meeting. "
                "Include disagreements and how they were resolved. "
                "Use past tense. Do NOT include decisions or action items here."
            ),
            "decisions": (
                "Outcomes that were agreed upon or resolved during the meeting. "
                "Look for phrases like 'we agreed', 'it was decided', 'we will go with'. "
                "Each decision should be a clear, standalone statement."
            ),
            "action_items": (
                "Look for ANY commitment made by a participant, including informal phrases like "
                "'I will prepare', 'I can write', 'let me contact', 'I will send', 'I will follow up'. "
                "These are action items even if not stated formally. "
                "task: What needs to be done, described clearly. "
                "owner: The person who made the commitment. "
                "due_date: Any date or timeframe mentioned. "
                "status: Open by default."
            ),
            "next_meeting": (
                "This refers to a FUTURE scheduled meeting. "
                "Use future tense. Include date, time, and purpose if mentioned."
            ),
            "notes": (
                "Any additional observations, reminders, or information mentioned "
                "that does not fit in the other sections."
            ),
        }

    else:
        persona = "expert business analyst extracting structured requirements from meeting transcripts"
        section_guidance = {
            "executive_summary": (
                "company_description: Look for any mention of what the company does, its industry, size, or background. "
                "This may appear as casual phrases like 'our company', 'we work in', 'our organization', 'The Company'. "
                "problem: The main issue or pain point driving this meeting. "
                "proposed_solution: The suggested fix or system. "
                "expected_benefits: Positive outcomes mentioned."
            ),
            "business_drivers": (
                "need_for_change: Why is the current situation no longer acceptable? "
                "goals: What does the organization want to achieve? These are high-level objectives, not system features. "
                "kpis: Any measurable targets or success metrics mentioned, such as percentages, numbers, or timeframes."
            ),
            "project_scope": (
                "in_scope: HIGH-LEVEL SYSTEM COMPONENTS or MODULES only. "
                "Do NOT include functional requirements here. "
                "out_of_scope: ONLY items explicitly mentioned as excluded. Do NOT invent out-of-scope items. "
                "assumptions: Things assumed to be true for the project to proceed. "
                "constraints: Limitations such as budget, time, resources, or dependencies."
            ),
            "stakeholders": (
                "These are ROLES or GROUPS involved in the project (e.g. IT team, management, end users). "
                "Do NOT include individual names unless they represent a role. "
                "Do NOT include meeting authors or approvers."
            ),
            "current_process": (
                "overview: How things currently work before this project. "
                "pain_points: Specific problems or frustrations with the current process mentioned in the meeting."
            ),
            "functional_requirements": (
                "These are features the SYSTEM must provide to users — specific USER ACTIONS or SYSTEM BEHAVIORS. "
                "Do NOT include high-level components (those belong in project_scope). "
                "Do NOT include meeting actions or things people plan to do manually outside the system. "
                "Each requirement must be one specific feature only."
            ),
            "non_functional_requirements": (
                "performance: Speed, response time, or load requirements. "
                "security: Access control, authentication, or data protection requirements. "
                "usability: Ease of use, accessibility, or interface requirements. "
                "Only include if explicitly mentioned in the transcript."
            ),
            "risk_analysis": (
                "Look for any concern, worry, or potential obstacle mentioned. "
                "Phrases like 'I am worried', 'what if', 'the risk is', 'this might delay' are indicators. "
                "description: What could go wrong. "
                "impact: How serious is it — High, Medium, or Low. "
                "probability: How likely is it — High, Medium, or Low."
            ),
            "document_control": (
                "authors: The people who created or are responsible for this document. "
                "approval: The people who need to approve it. "
                "version_history: Any mention of versions or dates."
            ),
            "glossary": (
                "term: The technical English word or abbreviation. "
                "definition: Its meaning in context. "
                "Do NOT swap term and definition. "
                "Include acronyms like ERP, KPI, API if mentioned and explained."
            ),
            "references": (
                "Any documents, standards, or sources mentioned in the meeting."
            ),
            "appendix": (
                "Any supplementary material, attachments, or additional information mentioned."
            ),
        }

    specific = section_guidance.get(section_name, "")
    if doc_type == "MOM":
        focus = f"Focus on: decisions, action items, attendees, agenda, discussion points. {specific}"
    else:
        focus = f"Focus on: requirements, scope, stakeholders, risks, objectives. {specific}"

    prompt = f"""You are an {persona}.

TASK:
Fill in the following JSON section using ONLY the information found in the provided transcript excerpts.
{focus}
Do NOT add information that is not in the transcript.
If information is not found, use null for strings and [] for arrays.

SECTION TO FILL:
{template_str}

TRANSCRIPT EXCERPTS:
{context}

RULES:
1. Return ONLY valid JSON matching the exact structure above.
2. Do NOT add extra fields.
3. Do NOT add explanations or text outside the JSON.
4. Use null for missing string values.
5. Use [] for missing array values.

JSON OUTPUT:"""

    raw    = _call_ollama(prompt)
    parsed = _safe_parse(raw)
    if isinstance(parsed, dict):
        return parsed
    return None