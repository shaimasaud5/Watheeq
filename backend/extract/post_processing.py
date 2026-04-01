import re


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_priority(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return None

    p = value.strip().lower()

    mapping = {
        "must have": "must-have",
        "must-have": "must-have",
        "should have": "should-have",
        "should-have": "should-have",
        "could have": "could-have",
        "could-have": "could-have",
        "null": None,
        "none": None,
        "": None,
    }
    return mapping.get(p, None)


def clean_functional_requirements(reqs):
    banned_phrases = [
        "assign priority levels",
        "must have, should have, and could have",
        "json",
        "schema",
        "extraction instructions",
        "return only",
    ]

    cleaned = []
    for item in ensure_list(reqs):
        if not isinstance(item, dict):
            continue

        desc = str(item.get("description") or "").strip()
        if not desc:
            continue

        low = desc.lower()
        if any(p in low for p in banned_phrases):
            continue

        cleaned.append({
            "description": desc,
            "priority": normalize_priority(item.get("priority")),
        })

    return cleaned


def normalize_version_history(items):
    normalized = []

    for item in ensure_list(items):
        if isinstance(item, dict):
            normalized.append({
                "date": item.get("date"),
                "changes": item.get("changes"),
            })
        elif isinstance(item, str):
            normalized.append({
                "date": item,
                "changes": None,
            })

    return normalized


def guess_names(text: str):
    pairs = re.findall(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", text)

    stop_first = {
        "Project", "Meeting", "Transcript", "Strategic",
        "The", "January", "February", "March", "April"
    }
    stop_last = {"Review", "Meeting", "Transcript"}

    out = []
    for f, l in pairs:
        if f in stop_first or l in stop_last:
            continue
        name = f"{f} {l}"
        if name not in out:
            out.append(name)
        if len(out) >= 6:
            break

    return out


def guess_risks(text: str):
    lines = re.split(r"[.?!]\s*", text)
    keywords = ("risk", "concern", "delay", "budget", "uncertain", "issue", "problem")
    hits = []

    for ln in lines:
        low = ln.lower()
        if any(k in low for k in keywords) and len(ln.strip()) > 10:
            hits.append(ln.strip())
        if len(hits) >= 5:
            break

    return hits


def post_process_extracted(extracted: dict, transcript: str) -> dict:
    # executive_summary
    es = extracted.get("executive_summary", {})
    es["expected_benefits"] = ensure_list(es.get("expected_benefits"))
    extracted["executive_summary"] = es

    # stakeholders fallback
    if isinstance(extracted.get("stakeholders"), list) and len(extracted["stakeholders"]) == 0:
        names = guess_names(transcript)
        if names:
            extracted["stakeholders"] = [
                {"name": n, "role": None, "responsibility": None} for n in names
            ]

    # risks fallback
    if isinstance(extracted.get("risk_analysis"), list) and len(extracted["risk_analysis"]) == 0:
        risks = guess_risks(transcript)
        if risks:
            extracted["risk_analysis"] = [
                {"risk": r, "impact": None, "likelihood": None, "mitigation": None}
                for r in risks
            ]

    # normalize risk structure
    if isinstance(extracted.get("risk_analysis"), list):
        fixed = []
        for item in extracted["risk_analysis"]:
            if isinstance(item, dict):
                normalized_item = {
                    "risk": item.get("risk"),
                    "impact": item.get("impact"),
                    "likelihood": item.get("likelihood"),
                    "mitigation": item.get("mitigation"),
                }

                if any(v not in [None, "", [], {}] for v in normalized_item.values()):
                    fixed.append(normalized_item)
            else:
                val = str(item).strip()
                if val:
                    fixed.append({
                        "risk": val,
                        "impact": None,
                        "likelihood": None,
                        "mitigation": None,
                    })
        extracted["risk_analysis"] = fixed

    # parse impact/likelihood from risk text
    if isinstance(extracted.get("risk_analysis"), list):
        for item in extracted["risk_analysis"]:
            if not isinstance(item, dict):
                continue

            risk_text = (item.get("risk") or "")
            m = re.search(r"\((.*?)\)", risk_text)
            if not m:
                continue

            inside = m.group(1).lower()

            if item.get("impact") is None:
                if "high impact" in inside:
                    item["impact"] = "High"
                elif "medium impact" in inside:
                    item["impact"] = "Medium"
                elif "low impact" in inside:
                    item["impact"] = "Low"

            if item.get("likelihood") is None:
                if "high likelihood" in inside:
                    item["likelihood"] = "High"
                elif "medium likelihood" in inside:
                    item["likelihood"] = "Medium"
                elif "low likelihood" in inside:
                    item["likelihood"] = "Low"

            item["risk"] = re.sub(r"\s*\(.*?\)\s*", " ", risk_text).strip()

    # stakeholders cleanup
    if isinstance(extracted.get("stakeholders"), list):
        org_words = {
            "committee", "steering", "board", "team", "department", "management",
            "analyst", "representative", "client", "customer", "users", "user",
            "stakeholder", "group", "office", "company", "vendor", "supplier"
        }

        bad_tokens = {
            "january", "february", "march", "april", "may", "june", "july", "august",
            "september", "october", "november", "december",
            "strategic", "review", "project", "meeting", "notes", "q1", "q2", "q3", "q4"
        }

        glossary_terms = set()
        if isinstance(extracted.get("glossary"), list):
            for g in extracted["glossary"]:
                if isinstance(g, dict):
                    term = g.get("term")
                    if isinstance(term, str):
                        glossary_terms.add(term.lower())

        cleaned = []
        for s in extracted["stakeholders"]:
            if not isinstance(s, dict):
                continue

            name = (s.get("name") or "").strip()
            if not name:
                continue

            if not re.fullmatch(r"[A-Za-z]+(?:\-[A-Za-z]+)?(?:\s+[A-Za-z]+(?:\-[A-Za-z]+)?)?", name):
                continue

            parts = [w.lower() for w in name.split()]
            w1 = parts[0]
            w2 = parts[1] if len(parts) > 1 else None

            if (w1 in org_words) or (w2 in org_words if w2 else False):
               continue

            if (w1 in bad_tokens) or (w2 in bad_tokens if w2 else False):
               continue

            lower_name = name.lower()
            if any(lower_name in term for term in glossary_terms):
                continue

            cleaned.append({
                "name": name,
                "role": s.get("role"),
                "responsibility": s.get("responsibility"),
            })

        extracted["stakeholders"] = cleaned

    # functional_requirements
    extracted["functional_requirements"] = clean_functional_requirements(
        extracted.get("functional_requirements", [])
    )

    # document_control
    dc = extracted.get("document_control", {})
    dc["version_history"] = normalize_version_history(dc.get("version_history"))
    dc["authors"] = ensure_list(dc.get("authors"))
    dc["approval"] = ensure_list(dc.get("approval"))
    extracted["document_control"] = dc

    # business_drivers
    bd = extracted.get("business_drivers", {})
    bd["goals"] = ensure_list(bd.get("goals"))
    bd["kpis"] = ensure_list(bd.get("kpis"))
    extracted["business_drivers"] = bd

    # project_scope
    ps = extracted.get("project_scope", {})
    ps["in_scope"] = ensure_list(ps.get("in_scope"))
    ps["out_of_scope"] = ensure_list(ps.get("out_of_scope"))
    ps["assumptions"] = ensure_list(ps.get("assumptions"))
    ps["constraints"] = ensure_list(ps.get("constraints"))
    extracted["project_scope"] = ps

    # current_process
    cp = extracted.get("current_process", {})
    cp["pain_points"] = ensure_list(cp.get("pain_points"))
    extracted["current_process"] = cp

    # non_functional_requirements
    nfr = extracted.get("non_functional_requirements", {})
    nfr["performance"] = ensure_list(nfr.get("performance"))
    nfr["security"] = ensure_list(nfr.get("security"))
    nfr["usability"] = ensure_list(nfr.get("usability"))
    extracted["non_functional_requirements"] = nfr

    extracted["references"] = ensure_list(extracted.get("references"))
    extracted["appendix"] = ensure_list(extracted.get("appendix"))

    return extracted
