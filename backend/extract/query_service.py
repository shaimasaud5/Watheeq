def get_query_by_doc_type(doc_type):
    doc_type = (doc_type or "").strip().upper()

    if doc_type == "MOM":
        return "meeting decisions motions amendments votes announcements action items"

    elif doc_type == "BRD":
        return "ai system requirements data sources functionality scope solution features platform analytics"

    else:
        return "general summary"