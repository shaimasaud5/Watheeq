# extract/extractor.py
# ─────────────────────
# Core extraction logic using the RAG approach.
#
# For each section in the schema:
# 1. Generate an embedding for the section name using the same model
#    from the Processing stage (mxbai-embed-large)
# 2. Compare it with all stored chunk embeddings
# 3. Retrieve the top 5 most similar chunks
# 4. Send the retrieved chunks to the LLM and ask it to extract
#    the value for that specific section
# 5. Combine all extracted sections into a complete filled_schema

import copy
from .embedding_service import generate_embedding
from .retrieval_service  import retrieve_top_chunks
from .llm_service        import extract_section
from .schemas            import BRD_SCHEMA, MOM_SCHEMA

SECTION_QUERIES = {
    # ═══ BRD ═══
    "executive_summary": (
        "company overview what the company does industry sector business background "
        "problem we are facing challenge current situation proposed solution new system "
        "benefits expected outcomes why we need this project"
    ),
    "business_drivers": (
        "why we need to change reason for this project business goal objective "
        "we want to achieve we need to improve we are losing we are struggling "
        "success measure KPI target percentage reduce increase save time cost"
    ),
    "project_scope": (
        "what is included in the project what will be built what will be developed "
        "what is not included will not be developed outside the scope "
        "we assume we are assuming constraint limitation deadline budget restriction "
        "depends on subject to approval"
    ),
    "stakeholders": (
        "team responsible for involved in affected by who will use who will manage "
        "development team management client end users HR IT department "
        "project manager product owner business analyst"
    ),
    "current_process": (
        "currently we do how it works now the existing system the old way "
        "the problem with the current process manually done takes too long "
        "error prone inefficient we spend time on we struggle with"
    ),
    "functional_requirements": (
        "the system should allow users to the system must the user can "
        "feature capability login register submit view track update delete search filter "
        "send notification generate report upload download approve reject"
    ),
    "non_functional_requirements": (
        "performance response time fast slow load handle concurrent users "
        "security authentication authorization encrypt protect access control "
        "easy to use user friendly available reliable backup recovery"
    ),
        "risk_analysis": (
        "risk concern worried might fail could delay challenge obstacle "
        "what if problem occurs dependency on team availability budget cut "
        "technical complexity integration difficulty timeline pressure"
    ),
    "document_control": (
        "prepared by written by author approved by version date created reviewed "
        "responsible for this document sign off"
    ),
    "glossary": (
        "term means definition stands for abbreviation acronym what is "
        "ERP KPI API CRM system name technical word explanation"
    ),
    "references": (
        "reference document standard guideline source based on according to "
        "mentioned in previous meeting attached document link"
    ),
    "appendix": (
        "additional information supplementary attached supporting material "
        "diagram chart table extra details see attached"
    ),

    # ═══ MOM ═══
    "meeting_info": (
        "meeting title subject agenda date time location held in room online at meeting room"
        " meeting was held on meeting started at zoom teams google meet facilitated  by"
    ),
    "attendees": (
        "present in the meeting attended joined participated "
        "who was in the meeting who spoke who joined the call "
        "on behalf of representing"
    ),
    "agenda": (
        "today we will discuss the agenda for this meeting topics to cover "
        "first item second item we planned to talk about purpose of this meeting"
    ),
    "discussion_summary": (
        "we discussed we talked about we reviewed we went through "
        "the team debated there was disagreement we considered options "
        "on one hand on the other hand the concern was the suggestion was "
        "after discussion we looked at the issue with"
    ),
    "decisions": (
        "we decided we agreed we resolved we concluded we will go with "
        "the decision is it was agreed that we chose we selected "
        "final decision approved rejected confirmed"
    ),
    "action_items": (
        "I will you will she will he will we will "
        "I am going to I can handle I will prepare I will send I will follow up "
        "let me contact let me check action item task assigned to "
        "responsible for by when due date deadline who will do this"
    ),
    "next_meeting": (
        "next meeting will be scheduled for let us meet again "
        "next week next month we will reconvene follow up meeting "
        "date time for next session shall we meet on"
    ),
    "notes": (
        "note to mention worth noting additionally side note "
        "reminder for the record just to mention also discussed "
        "miscellaneous other points raised"
    ),
}
def _merge(template, extracted):
    """
    Merge the LLM result into the template structure.

    Preserves the original template structure if the LLM
    returns invalid or incomplete data.
    """
    if isinstance(template, dict):
        if not isinstance(extracted, dict):
            return template
        result = copy.deepcopy(template)
        for key in template:
            if key in extracted:
                result[key] = _merge(template[key], extracted[key])
        return result
    if isinstance(template, list):
        return extracted if isinstance(extracted, list) else template
    return extracted if extracted is not None else template


def _extract(schema: dict, chunks: list, doc_type: str) -> dict:
    """
    Main orchestration function used for both BRD and MOM generation.

    chunks: List of dictionaries in the format:
            {"semantic_english_text": str, "embedding": list}

            Retrieved from TranscriptChunk generated in Task 2.
    """
    filled = copy.deepcopy(schema)

    for section_name, section_template in schema.items():
        print(f"  [ {doc_type} ] Extracting: {section_name}...")

         # 1. Generate embedding for the section name
        query = SECTION_QUERIES.get(section_name, section_name)
        section_embedding = generate_embedding(query)

        # 2. Retrieve the top 5 most similar chunks
        top_chunks = retrieve_top_chunks(
            section_embedding=section_embedding,
            chunks=chunks,
            top_k=5,
        )

         # 3. Combine retrieved chunks into a single context
        context = "\n\n---\n\n".join(top_chunks)

        # 4. Send the context to the LLM and extract the section value
        result = extract_section(section_name, section_template, context, doc_type)

        # 5. Merge the result into the final schema
        #    If extraction fails, keep the original empty template
        if result and section_name in result:
            filled[section_name] = _merge(section_template, result[section_name])

    return filled


def extract_brd(chunks: list) -> dict:
    """Extract filled_schema for BRD document."""
    return _extract(BRD_SCHEMA, chunks, "BRD")


def extract_mom(chunks: list) -> dict:
    """Extract filled_schema for MOM document."""
    return _extract(MOM_SCHEMA, chunks, "MOM")
