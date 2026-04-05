# def detect_schema_type(schema: dict) -> str:
#     if not isinstance(schema, dict):
#         return "GENERIC"

#     properties = schema.get("properties", {}) or {}
#     keys = set(properties.keys())

#     brd_keys = {
#         "document_control",
#         "executive_summary",
#         "business_drivers",
#         "project_scope",
#         "current_process",
#         "risk_analysis",
#         "functional_requirements",
#         "non_functional_requirements",
#     }

#     mom_keys = {
#         "meeting_title",
#         "meeting_date",
#         "attendees",
#         "agenda_items",
#         "discussion_points",
#         "decisions_made",
#         "action_items",
#         "next_steps",
#     }

#     if len(keys.intersection(brd_keys)) >= 4:
#         return "BRD"

#     if len(keys.intersection(mom_keys)) >= 4:
#         return "MOM"

#     return "GENERIC"