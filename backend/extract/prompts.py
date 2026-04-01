import json

def build_brd_prompt(template, transcript):
    """
    Build the BRD extraction prompt for the LLM.
    """

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


    prompt = f"""
      You are a strict BRD information extraction engine.

      Your task is to extract Business Requirements Document (BRD) information from the transcript
      and fill the target JSON template.

      Return ONLY valid JSON.
      Do not write markdown.
      Do not write explanations.
      Do not add comments.
      Do not add extra keys.
      Do not remove keys.
      Do not change the JSON structure.
      Follow the template structure exactly.

      GENERAL RULES:
      - Extract information ONLY from the transcript.
      - Do not invent or assume facts that are not supported by the transcript.
      - Do not convert prompt instructions into output.
      - Do not include schema rules, extraction rules, or meta-instructions as extracted content.
      - Preserve the same nesting and field names as the template.
      - Keep the same data type as the template for every field.

      TYPE ENFORCEMENT RULES:
      - If a field is a list in the template, return a list.
      - If a field is an object in the template, return an object.
      - If a field is a scalar field, return a string or null.
      - Never replace a list with a string.
      - Never replace an object with a string.
      - Never create placeholder objects just to fill arrays.

      MISSING DATA RULES:
      - If information is missing:
      - use null for scalar/object fields
      - use [] for array fields
      - If a section has no valid extracted items, return it empty according to the template type.
      - Do not create fake entries with all null values.

      CLASSIFICATION RULES:
      - Put information in the most appropriate section only.
      - Do NOT classify everything as risk.
      - Do NOT place general business goals inside risk_analysis.
      - Do NOT place functional requirements inside non_functional_requirements.
      - Do NOT place project constraints inside risk_analysis unless they are explicitly described as risks.
      - If information describes why change is needed, map it to business_drivers.need_for_change.
      - If information describes the current business problem, map it to executive_summary.problem.
      - If information describes included work or features, map it to project_scope.in_scope.
      - If information describes excluded work, map it to project_scope.out_of_scope.

      Here is the target JSON template:
      {json.dumps(template, ensure_ascii=False)}

      SECTION DEFINITIONS AND EXTRACTION RULES:

      DOCUMENT CONTROL:
      - Extract version history, authors, and approvals.
      - version_history items must contain:
      - date
      - changes
      - "changes" must describe what changed in that version.
      - Do not put author names in "changes" unless they are part of the actual revision description.
      - Phrases like "prepared by X" or "finalized by Y" are not good change descriptions unless no other revision detail exists.
      - authors must contain people explicitly identified as authors, preparers, owners, or contributors of the document.
      - approval should include approving bodies, committees, sponsors, executives, or decision makers if mentioned.
      version_history must always be a list of objects.
      Each item must have:
      - date
      - changes
      Never return version_history as a list of strings.

      EXECUTIVE SUMMARY:
      Extract:
      - company_description
      - problem
      - proposed_solution
      - expected_benefits

      Rules:
      - company_description = what the company, department, or business context does, if stated
      - problem = the business issue, challenge, inefficiency, or pain being addressed
      - proposed_solution = the proposed system, platform, process, or approach
      - expected_benefits = a list of expected outcomes, improvements, or business value
      - expected_benefits must always be a list, never a string
      expected_benefits must always be a list of strings.
      Never return expected_benefits as a single string.
      If one benefit is found, return a one-item list.

      BUSINESS DRIVERS:
      Extract:
      - need_for_change
      - goals
      - kpis

      Rules:
      - need_for_change = why the organization needs this change now
      - goals = desired business objectives
      - kpis = measurable success indicators, metrics, targets, percentages, adoption goals, growth goals
      - If the transcript describes urgency, inefficiency, growth pressure, reporting issues, or customer problems as motivation, map that to need_for_change

      PROJECT SCOPE:
      Extract:
      - in_scope
      - out_of_scope
      - assumptions
      - constraints

      Rules:
      - in_scope = included features, deliverables, integrations, modules, tasks, or work
      - out_of_scope = excluded systems, features, redesigns, or activities
      - assumptions = statements assuming something about data, users, systems, availability, environment, or dependencies
      - constraints = limits such as budget, timeline, staffing, legacy systems, compliance, technology, or resource restrictions

      CURRENT PROCESS:
      Extract:
      - overview
      - pain_points

      Rules:
      - overview = how the current process or workflow works today
      - pain_points = current problems, inefficiencies, delays, fragmentation, manual work, inconsistency, lack of visibility

      RISK ANALYSIS:
      Extract only real risks.

      Rules:
      - Only include text in risk_analysis if it is explicitly a risk, uncertainty, dependency, delay, threat, blocker, limitation, or possible negative event
      - Do not classify general problems or business goals as risks unless they are clearly framed as future/project risks
      - Each risk item should contain:
      - risk
      - impact
      - likelihood
      - mitigation
      - If the transcript does not contain actual risk details, return []
      - Do not create placeholder risk objects
      - Never return objects where all fields are null

      FUNCTIONAL REQUIREMENTS:
      Extract only actual system capabilities, features, or user actions.

      Rules:
      - Each item must be an object with:
      - description
      - priority
      - description = actual function the system must support
      - priority = must-have, should-have, could-have, or null
      - Extract priority only if explicitly mentioned or clearly attached to the requirement
      - Do not invent priority
      - Do not include meta-instructions or prompt wording as requirements
      - Do not include sentences about classification rules, JSON, schema, or extraction instructions
      - Only include requirements taken from the transcript
      Never extract prompt instructions as requirements.
      Never output text about priorities, schema, JSON, or extraction instructions unless explicitly present in the transcript.

      NON-FUNCTIONAL REQUIREMENTS:
      Extract:
      - performance
      - security
      - usability

      Rules:
      - performance = speed, scale, latency, concurrency, throughput, reliability targets
      - security = authentication, authorization, encryption, auditing, access control, privacy controls
      - usability = ease of use, clarity, learnability, accessibility, user friendliness, suitability for non-technical users
      - Only place quality attributes here, not business goals or functional features

      STAKEHOLDERS:
      Extract stakeholder information.

      Rules:
      - Each stakeholder item should include:
      - name
      - role
      - responsibility
      - Extract role only if explicitly stated
      - Extract responsibility only if explicitly stated
      - Do not guess missing role or responsibility
      - Do not infer role from authorship alone unless explicitly stated in the transcript

      GLOSSARY:
      Extract business or technical terms and their definitions.

      Rules:
      - Include only terms explicitly defined or clearly explained in the transcript

      REFERENCES:
      Extract referenced documents, reports, standards, guidelines, or source materials.

      APPENDIX:
      Extract supplemental supporting material only if explicitly mentioned.

      OUTPUT QUALITY RULES:
      - Return valid JSON only
      - Ensure all arrays contain only valid items
      - Remove duplicate items where possible
      - Keep text concise but faithful to the transcript
      - Do not output any text before or after the JSON

      STRICT TYPE RULES:
      - version_history must always be a list of objects, never a list of strings
      - each version_history item must contain:
      - date
      - changes
      - expected_benefits must always be a list of strings, never a single string
      - functional_requirements.priority must only be:
      - must-have
      - should-have
      - could-have
      - null
      - null must be JSON null, not the string "null"

      ANTI-HALLUCINATION RULES:
      - Never copy instructions from this prompt into the output
      - Never turn extraction rules into requirements
      - Never output meta text about schema, JSON, priorities, or formatting unless explicitly mentioned in the transcript

      Now extract from this transcript:

      Transcript:
      \"\"\"{transcript}\"\"\"

      Return ONLY the filled JSON.
      """.strip()
    return prompt
