import copy


ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_STATUSES = {"open", "in progress", "completed", "pending", "blocked"}


def normalize_text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return " ".join(value.strip().split())


def normalize_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "1"}:
            return True
        if v in {"false", "no", "0", ""}:
            return False

    if isinstance(value, (int, float)):
        return bool(value)

    return False


def ensure_dict(value):
    return value if isinstance(value, dict) else {}


def ensure_list(value):
    return value if isinstance(value, list) else []


def deduplicate_strings(items):
    cleaned = []
    seen = set()

    for item in ensure_list(items):
        text = normalize_text(item)
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(text)

    return cleaned


def clean_person_list(items):
    cleaned = []
    seen = set()

    for item in ensure_list(items):
        if isinstance(item, str):
            name = normalize_text(item)
            role = ""
        elif isinstance(item, dict):
            name = normalize_text(item.get("name"))
            role = normalize_text(item.get("role"))
        else:
            continue

        if not name:
            continue

        key = (name.lower(), role.lower())
        if key in seen:
            continue

        seen.add(key)
        cleaned.append({
            "name": name,
            "role": role
        })

    return cleaned


def clean_meeting_details(data):
    data = ensure_dict(data)

    return {
        "project_name": normalize_text(data.get("project_name")),
        "meeting_title": normalize_text(data.get("meeting_title")),
        "date": normalize_text(data.get("date")),
        "start_time": normalize_text(data.get("start_time")),
        "end_time": normalize_text(data.get("end_time")),
        "location_or_platform": normalize_text(data.get("location_or_platform")),
    }


def clean_attendees(data):
    data = ensure_dict(data)

    return {
        "participants": clean_person_list(data.get("participants")),
        "absentees": clean_person_list(data.get("absentees")),
    }


def clean_agenda_and_objectives(data):
    data = ensure_dict(data)

    return {
        "agenda": deduplicate_strings(data.get("agenda")),
        "meeting_objectives": deduplicate_strings(data.get("meeting_objectives")),
    }


def clean_discussion_points(items):
    cleaned = []
    seen = set()

    for item in ensure_list(items):
        if isinstance(item, str):
            topic = ""
            summary = normalize_text(item)
            key_points = []
        elif isinstance(item, dict):
            topic = normalize_text(item.get("topic"))
            summary = normalize_text(item.get("summary"))
            key_points = deduplicate_strings(item.get("key_points"))
        else:
            continue

        if not topic and not summary and not key_points:
            continue

        if not summary and key_points:
            summary = "; ".join(key_points)

        key = (
            topic.lower(),
            summary.lower(),
            tuple(k.lower() for k in key_points)
        )

        if key in seen:
            continue

        seen.add(key)
        cleaned.append({
            "topic": topic,
            "summary": summary,
            "key_points": key_points
        })

    return cleaned


def normalize_priority(value):
    value = normalize_text(value).lower()
    if value in ALLOWED_PRIORITIES:
        return value.title()

    mapping = {
        "urgent": "High",
        "critical": "High",
        "high priority": "High",
        "medium priority": "Medium",
        "normal": "Medium",
        "moderate": "Medium",
        "low priority": "Low",
    }
    return mapping.get(value, "")


def normalize_status(value):
    value = normalize_text(value).lower()
    if value in ALLOWED_STATUSES:
        if value == "in progress":
            return "In Progress"
        return value.title()

    mapping = {
        "not started": "Open",
        "todo": "Open",
        "to do": "Open",
        "ongoing": "In Progress",
        "done": "Completed",
        "complete": "Completed",
        "waiting": "Pending",
        "on hold": "Pending",
        "at risk": "Blocked",
    }
    return mapping.get(value, "")


def looks_like_vague_task(task):
    vague_values = {
        "",
        "follow up",
        "to be discussed",
        "discussion",
        "review",
        "check",
        "update",
        "pending",
        "n/a",
        "na",
        "none",
    }
    return task.strip().lower() in vague_values


def clean_action_items(items):
    cleaned = []
    seen = set()

    for item in ensure_list(items):
        if isinstance(item, str):
            task = normalize_text(item)
            assigned_to = ""
            deadline = ""
            priority = ""
            status = ""
        elif isinstance(item, dict):
            task = normalize_text(item.get("task"))
            assigned_to = normalize_text(item.get("assigned_to"))
            deadline = normalize_text(item.get("deadline"))
            priority = normalize_priority(item.get("priority"))
            status = normalize_status(item.get("status"))
        else:
            continue

        if not task or looks_like_vague_task(task):
            continue

        key = (
            task.lower(),
            assigned_to.lower(),
            deadline.lower()
        )
        if key in seen:
            continue

        seen.add(key)
        cleaned.append({
            "task": task,
            "assigned_to": assigned_to,
            "deadline": deadline,
            "priority": priority,
            "status": status
        })

    return cleaned


def looks_like_fake_decision(text):
    bad_values = {
        "",
        "discussed",
        "under discussion",
        "to be decided",
        "pending",
        "n/a",
        "na",
        "none",
    }
    return text.strip().lower() in bad_values


def clean_key_decisions(items):
    cleaned = []
    seen = set()

    for item in ensure_list(items):
        if isinstance(item, str):
            decision = normalize_text(item)
            impact = ""
        elif isinstance(item, dict):
            decision = normalize_text(item.get("decision"))
            impact = normalize_text(item.get("impact"))
        else:
            continue

        if not decision or looks_like_fake_decision(decision):
            continue

        key = (decision.lower(), impact.lower())
        if key in seen:
            continue

        seen.add(key)
        cleaned.append({
            "decision": decision,
            "impact": impact
        })

    return cleaned


def clean_future_meeting(data):
    data = ensure_dict(data)

    required = normalize_bool(data.get("required"))
    proposed_date = normalize_text(data.get("proposed_date"))
    purpose = normalize_text(data.get("purpose"))

    if not proposed_date and not purpose:
        required = False

    return {
        "required": required,
        "proposed_date": proposed_date,
        "purpose": purpose
    }


def clean_follow_up_items(data):
    data = ensure_dict(data)

    return {
        "next_steps": deduplicate_strings(data.get("next_steps")),
        "future_meeting": clean_future_meeting(data.get("future_meeting"))
    }


def clean_additional_notes(items):
    return deduplicate_strings(items)


def clean_supporting_documents(items):
    cleaned = []
    seen = set()

    for item in ensure_list(items):
        if isinstance(item, str):
            document_name = normalize_text(item)
            reference = ""
        elif isinstance(item, dict):
            document_name = normalize_text(item.get("document_name"))
            reference = normalize_text(item.get("reference"))
        else:
            continue

        if not document_name and not reference:
            continue

        key = (document_name.lower(), reference.lower())
        if key in seen:
            continue

        seen.add(key)
        cleaned.append({
            "document_name": document_name,
            "reference": reference
        })

    return cleaned


def get_default_mom_structure():
    return {
        "meeting_details": {
            "project_name": "",
            "meeting_title": "",
            "date": "",
            "start_time": "",
            "end_time": "",
            "location_or_platform": ""
        },
        "attendees": {
            "participants": [],
            "absentees": []
        },
        "agenda_and_objectives": {
            "agenda": [],
            "meeting_objectives": []
        },
        "discussion_points": [],
        "action_items": [],
        "key_decisions": [],
        "follow_up_items": {
            "next_steps": [],
            "future_meeting": {
                "required": False,
                "proposed_date": "",
                "purpose": ""
            }
        },
        "additional_notes": [],
        "supporting_documents": []
    }


def post_process_mom(extracted):
    """
    Clean and normalize raw MOM extraction output from the LLM.
    Always returns a schema-safe dictionary.
    """
    extracted = ensure_dict(extracted)
    result = copy.deepcopy(get_default_mom_structure())

    result["meeting_details"] = clean_meeting_details(extracted.get("meeting_details"))
    result["attendees"] = clean_attendees(extracted.get("attendees"))
    result["agenda_and_objectives"] = clean_agenda_and_objectives(
        extracted.get("agenda_and_objectives")
    )
    result["discussion_points"] = clean_discussion_points(
        extracted.get("discussion_points")
    )
    result["action_items"] = clean_action_items(extracted.get("action_items"))
    result["key_decisions"] = clean_key_decisions(extracted.get("key_decisions"))
    result["follow_up_items"] = clean_follow_up_items(extracted.get("follow_up_items"))
    result["additional_notes"] = clean_additional_notes(extracted.get("additional_notes"))
    result["supporting_documents"] = clean_supporting_documents(
        extracted.get("supporting_documents")
    )

    return result