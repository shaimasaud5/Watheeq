# from django.shortcuts import render
# from pathlib import Path
# import json
# import re
# import requests

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import AllowAny


# class ExtractAPIView(APIView):
   
#     permission_classes = [AllowAny]

#     OLLAMA_URL = "http://ollama:11434/api/generate"
#     MODEL_NAME = "llama3.2" 

    

#     def post(self, request, *args, **kwargs):
#         transcript = request.data.get("transcript")
#         if not transcript or not isinstance(transcript, str):
#             return Response(
#                 {"error": "Please provide 'transcript' as a string."},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         schema = self._load_schema()
#         if isinstance(schema, Response):
#             return schema  
        
#         templet = self._empty_from_schema(schema)
#         extracted=templet.copy()

#         # LLM
#         llm_result = self._extract_with_llm(transcript, schema)
#         if llm_result is not None:
#             #دمج الناتج على القالب (عشان نضمن نفس المفاتيح دائمًا)
#             extracted = self._merge_into_template(extracted, llm_result)
            
#             for k, v in extracted.items():
#                 if v == "null":
#                     extracted[k] = None

#         result = {
#             "status": "ok",
#             "received_chars": len(transcript),
#             "preview": transcript[:120],
#             "extracted": extracted,
#         }
#         return Response(result, status=status.HTTP_200_OK)

#     # helpers 

#     def _load_schema(self):
#         schema_path = Path(__file__).parent / "schema.json"
#         if not schema_path.exists():
#             return Response(
#                 {"error": "schema.json not found in extract app folder."},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
#         try:
#             return json.loads(schema_path.read_text(encoding="utf-8"))
#         except Exception as e:
#             return Response(
#                 {"error": f"Failed to read schema.json: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#     def _empty_from_schema(self, schema: dict):
        
#         t = schema.get("type")

#         if t == "object":
#             props = schema.get("properties", {}) or {}
#             out = {}
#             for k, subschema in props.items():
#                 out[k] = self._empty_from_schema(subschema)
#             return out

#         if t == "array":
#             # نخليها فاضية، والـ LLM يعبيها لو قدر
#             return []

#         # string / number / boolean / ... => None
#         return None

#     def _merge_into_template(self, template, llm_data):
#         """
#         يدمج llm_data داخل template بدون ما يطلع برا مفاتيح template.
#         - dict داخل dict => merge recursive
#         - list => replace (إذا llm_data list)
#         - scalar => replace
#         """
#         if isinstance(template, dict):
#             if not isinstance(llm_data, dict):
#                 return template
#             for k in template.keys():
#                 if k in llm_data:
#                     template[k] = self._merge_into_template(template[k], llm_data[k])
#             return template

#         if isinstance(template, list):
#             return llm_data if isinstance(llm_data, list) else template

#         # scalar
#         return llm_data if llm_data is not None else template

#     def _safe_json_loads(self, text: str):
#         """
#         يحاول يطلع JSON حتى لو رجّع المودل نص وفيه زيادة
#         """
#         if not text:
#             return None

#         text = text.strip()

#         # إذا الرد عبارة عن JSON صريح
#         try:
#             return json.loads(text)
#         except:
#             pass

#         # محاولة استخراج أول { ... } أو [ ... ]
#         m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
#         if not m:
#             return None

#         try:
#             return json.loads(m.group(1))
#         except:
#             return None


#     def _schema_brief(self, schema: dict) -> dict:
#         """
#         نرسل للمودل نسخة أخف من السكيما: properties + required فقط (بدون تفاصيل ضخمة)
#         """
#         return {
#             "type": schema.get("type", "object"),
#             "required": schema.get("required", []),
#             "properties": schema.get("properties", {}),
#         }


#     def _extract_with_llm(self, transcript: str, schema: dict):
#         # 1) template جاهز بنفس شكل السكيما
#         template = self._empty_from_schema(schema)  # يعطي None و [] على حسب النوع

#         # 2) سكيمة مختصرة عشان ما يتنفخ البرومبت
#         schema_brief = self._schema_brief(schema)

#         # 3) برومبت احترافي: نعطيه (schema + template) ونلزمه يرجّع JSON فقط
#         prompt = f"""
# You are a strict information extraction engine.

# Return ONLY valid JSON matching the schema keys exactly.

# Rules:
# - Use the transcript to infer values even if phrased indirectly.
# - Do NOT invent facts that are not supported by the transcript.
# - If a section is mentioned but details are missing, summarize what is mentioned.
# - For lists: if you find at least 1 item, return it; otherwise [].
# - For scalars/objects: if you find partial info, fill what you can and keep the rest null.

# Transcript:
# \"\"\"{transcript}\"\"\"
# """

#         payload = {
#             "model": self.MODEL_NAME,         # مثال: "llama3.2"
#             "prompt": prompt,
#             "stream": False,
#             "format": "json",                # مهم: يلزم المودل يحاول يطلع JSON
#             "options": {
#                 "temperature": 0
#             }
#         }

#         resp = requests.post(self.OLLAMA_URL, json=payload, timeout=350)
#         if resp.status_code != 200:
#             # رجعي None عشان النظام يكمل بالقالب الفاضي بدل ما يطيّح
#             return None

#         data = resp.json()
#         raw = data.get("response", "")
#         parsed = self._safe_json_loads(raw)

#         # parsed لازم يكون dict مطابق للـ template
#         if not isinstance(parsed, dict):
#             return None

#         return parsed
#     def _extract_first_json_object(self, text: str):
#         match = re.search(r"\{.*\}", text, flags=re.DOTALL)
#         return match.group(0) if match else None

from pathlib import Path
import json
import re
import requests

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class ExtractAPIView(APIView):
    permission_classes = [AllowAny]

    OLLAMA_URL = "http://ollama:11434/api/generate"
    MODEL_NAME = "llama3.2"

    def post(self, request, *args, **kwargs):
        transcript = request.data.get("transcript")
        if not transcript or not isinstance(transcript, str):
            return Response(
                {"error": "Please provide 'transcript' as a string."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        schema = self._load_schema()
        if isinstance(schema, Response):
            return schema

        template = self._empty_from_schema(schema)
        extracted = json.loads(json.dumps(template))  # deep copy

        llm_result = self._extract_with_llm(transcript, schema)
        if isinstance(llm_result, dict):
            extracted = self._merge_into_template(extracted, llm_result)

        # ✅ تنظيف احترافي بعد الدمج
        extracted = self._post_process(extracted, transcript)

        return Response(
            {
                "status": "ok",
                "received_chars": len(transcript),
                "preview": transcript[:120],
                "extracted": extracted,
            },
            status=status.HTTP_200_OK,
        )

    # ---------------- helpers ----------------

    def _load_schema(self):
        schema_path = Path(__file__).parent / "schema.json"
        if not schema_path.exists():
            return Response(
                {"error": "schema.json not found in extract app folder."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            return json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as e:
            return Response(
                {"error": f"Failed to read schema.json: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _empty_from_schema(self, schema: dict):
        t = schema.get("type")
        if t == "object":
            props = schema.get("properties", {}) or {}
            out = {}
            for k, subschema in props.items():
                out[k] = self._empty_from_schema(subschema)
            return out
        if t == "array":
            return []
        return None

    def _merge_into_template(self, template, llm_data):
        if isinstance(template, dict):
            if not isinstance(llm_data, dict):
                return template
            for k in template.keys():
                if k in llm_data:
                    template[k] = self._merge_into_template(template[k], llm_data[k])
            return template

        if isinstance(template, list):
            return llm_data if isinstance(llm_data, list) else template

        return llm_data if llm_data is not None else template

    def _safe_json_loads(self, text: str):
        if not text:
            return None
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    # ---------------- LLM ----------------

    def _extract_with_llm(self, transcript: str, schema: dict):
        # نرسل للمودل "شكل النتيجة" (template) بدل تفاصيل ضخمة
        template = self._empty_from_schema(schema)
        template_json = json.dumps(template, ensure_ascii=False)

        prompt = f"""
You are a strict BRD information extraction engine.

Return ONLY valid JSON.
Do not write markdown.
Do not write explanations.
Do not add extra keys.
Follow the schema structure exactly.

If information is missing:
- use null for scalar/object fields
- use [] for array fields

Do NOT classify everything as risk.
Only put text in risk_analysis if it is explicitly a risk, uncertainty, delay, threat, or constraint.

Here is the target JSON template:
{json.dumps(template, ensure_ascii=False)}

DOCUMENT CONTROL RULES:
- version_history items must contain: date and changes (not author).
- approval should include decision makers like committees or executives if mentioned.

FUNCTIONAL REQUIREMENTS RULES:
- Each item must be an object with:
  - description
  - priority (must-have / should-have / could-have if mentioned)
  - If a requirement mentions priority words like must-have, should-have, or could-have, extract them into the priority field.

PROJECT SCOPE RULES:
- assumptions must include statements that assume something about data, systems, or environment.
- constraints must include budget, timeline, or resource limits.

Example 1

Transcript:
"Meeting notes: The company operates in e-commerce analytics. The team said customer churn is rising because dashboards are outdated and engagement is not personalized. They plan to build a centralized analytics platform with customer segmentation and live dashboards. Expected benefits include faster decisions and improved retention. Main goals are improving retention and increasing campaign efficiency. KPIs include retention growth and dashboard adoption. In scope are dashboard development and CRM integration. Out of scope is replacing the ERP. Reporting is currently manual through spreadsheets, causing delays and inconsistent figures. Risks include budget uncertainty with high impact and high likelihood, mitigated by phased rollout. Sarah Ahmed is the Project Manager, Sulaiman Khan is the Business Analyst, and Nora is the Client Representative. Glossary term: Segmentation Engine means the automated module that groups customers by behavior. Reference: Q4 Market Analysis Report. Appendix: financial projections."

Output:
{{
  "document_control": {{
    "version_history": [],
    "authors": [
      {{"name": "Sarah Ahmed", "role": "Project Manager"}},
      {{"name": "Sulaiman Khan", "role": "Business Analyst"}},
      {{"name": "Nora", "role": "Client Representative"}}
    ],
    "approval": []
  }},
  "executive_summary": {{
    "company_description": "The company operates in e-commerce analytics.",
    "problem": "Customer churn is rising because dashboards are outdated and engagement is not personalized.",
    "proposed_solution": "Build a centralized analytics platform with customer segmentation and live dashboards.",
    "expected_benefits": "Faster decisions and improved retention."
  }},
  "business_drivers": {{
    "need_for_change": true,
    "goals": ["improving retention", "increasing campaign efficiency"],
    "kpis": ["retention growth", "dashboard adoption"]
  }},
  "project_scope": {{
    "in_scope": ["dashboard development", "CRM integration"],
    "out_of_scope": ["replacing the ERP"],
    "assumptions": [],
    "constraints": []
  }},
  "current_process": {{
    "overview": "Reporting is currently manual through spreadsheets.",
    "pain_points": ["delays", "inconsistent figures"]
  }},
  "risk_analysis": [
    {{
      "risk": "budget uncertainty",
      "impact": "High",
      "likelihood": "High",
      "mitigation": "phased rollout"
    }}
  ],
  "functional_requirements": [],
  "non_functional_requirements": {{
    "performance": [],
    "security": [],
    "usability": []
  }},
  "stakeholders": [
    {{"name": "Sarah Ahmed", "role": "Project Manager", "responsibility": null}},
    {{"name": "Sulaiman Khan", "role": "Business Analyst", "responsibility": null}},
    {{"name": "Nora", "role": "Client Representative", "responsibility": null}}
  ],
  "glossary": [
    {{"term": "Segmentation Engine", "description": "The automated module that groups customers by behavior."}}
  ],
  "references": [
    {{"name": "Q4 Market Analysis Report", "description": null}}
  ],
  "appendix": [
    {{"name": "financial projections", "description": null}}
  ]
}}

Example 2

Transcript:
"The session was only a scheduling check. No project details, risks, scope, goals, KPIs, references, glossary terms, or stakeholders were discussed."

Output:
{{
  "document_control": {{
    "version_history": [],
    "authors": [],
    "approval": []
  }},
  "executive_summary": {{
    "company_description": null,
    "problem": null,
    "proposed_solution": null,
    "expected_benefits": null
  }},
  "business_drivers": {{
    "need_for_change": null,
    "goals": [],
    "kpis": []
  }},
  "project_scope": {{
    "in_scope": [],
    "out_of_scope": [],
    "assumptions": [],
    "constraints": []
  }},
  "current_process": {{
    "overview": null,
    "pain_points": []
  }},
  "risk_analysis": [],
  "functional_requirements": [],
  "non_functional_requirements": {{
    "performance": [],
    "security": [],
    "usability": []
  }},
  "stakeholders": [],
  "glossary": [],
  "references": [],
  "appendix": []
}}

Now extract from this transcript:

Transcript:
\"\"\"{transcript}\"\"\"

Return ONLY the filled JSON.
""".strip()


        payload = {
            "model": self.MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }

        try:
            resp = requests.post(self.OLLAMA_URL, json=payload, timeout=350)
            resp.raise_for_status()
            raw = resp.json().get("response", "")
        except Exception:
            return None

        parsed = self._safe_json_loads(raw)
        return parsed if isinstance(parsed, dict) else None

    # ---------------- Post-processing ----------------

    def _post_process(self, extracted: dict, transcript: str) -> dict:
        # 1) expected_benefits لو طلعت list/غلط -> نحولها string
        try:
            benefits = extracted.get("executive_summary", {}).get("expected_benefits")
            if isinstance(benefits, list):
                extracted["executive_summary"]["expected_benefits"] = " ".join(
                    [str(x) for x in benefits]
                )
        except Exception:
            pass

        # 2) stakeholders fallback لو فاضية: نلقط أسماء من النص (بسيط)
        if isinstance(extracted.get("stakeholders"), list) and len(extracted["stakeholders"]) == 0:
            names = self._guess_names(transcript)
            if names:
                extracted["stakeholders"] = [
                    {"name": n, "role": None, "responsibility": None} for n in names
                ]

        # 3) risk_analysis fallback لو فاضي: نلقط جمل فيها risk/concern/delay/budget
        if isinstance(extracted.get("risk_analysis"), list) and len(extracted["risk_analysis"]) == 0:
            risks = self._guess_risks(transcript)
            if risks:
                extracted["risk_analysis"] = [
                    {"risk": r, "impact": None, "likelihood": None, "mitigation": None}
                    for r in risks
                ]

        # 4) risk_analysis: تأكدي كل عنصر فيه impact/likelihood/mitigation حتى لو المودل نساها
        if isinstance(extracted.get("risk_analysis"), list):
            fixed = []
            for item in extracted["risk_analysis"]:
                if isinstance(item, dict):
                    fixed.append({
                        "risk": item.get("risk"),
                        "impact": item.get("impact"),
                        "likelihood": item.get("likelihood"),
                        "mitigation": item.get("mitigation"),
                    })
                else:
                    fixed.append({
                        "risk": str(item),
                        "impact": None,
                        "likelihood": None,
                        "mitigation": None,
                    })
            extracted["risk_analysis"] = fixed

        # 5) risk_analysis: parse "(high impact, medium likelihood)" into fields
        if isinstance(extracted.get("risk_analysis"), list):
            for item in extracted["risk_analysis"]:
                if not isinstance(item, dict):
                    continue

                risk_text = (item.get("risk") or "")
                m = re.search(r"\((.*?)\)", risk_text)
                if not m:
                    continue

                inside = m.group(1).lower()

                # impact
                if item.get("impact") is None:
                    if "high impact" in inside:
                        item["impact"] = "High"
                    elif "medium impact" in inside:
                        item["impact"] = "Medium"
                    elif "low impact" in inside:
                        item["impact"] = "Low"

                # likelihood
                if item.get("likelihood") is None:
                    if "high likelihood" in inside:
                        item["likelihood"] = "High"
                    elif "medium likelihood" in inside:
                        item["likelihood"] = "Medium"
                    elif "low likelihood" in inside:
                        item["likelihood"] = "Low"

                # نظّف النص: شيل القوسين من risk
                item["risk"] = re.sub(r"\s*\(.*?\)\s*", "", risk_text).strip()

       # 6) stakeholders: keep only person-like names
        if isinstance(extracted.get("stakeholders"), list):
            # كلمات إذا ظهرت غالبًا معناها جهة/دور مو شخص
            ORG_WORDS = {
                "committee", "steering", "board", "team", "department", "management",
                "analyst", "representative", "client", "customer", "users", "user",
                "stakeholder", "group", "office", "company", "vendor", "supplier"
            }

            # استبعاد كلمات/شهور شائعة تطلع غلط
            BAD_TOKENS = {
                "january","february","march","april","may","june","july","august",
                "september","october","november","december",
                "strategic","review","project","meeting","notes","q1","q2","q3","q4"
            }

            # لو فيه glossary، نستبعد أي اسم هو جزء من مصطلح في القلوسري
            glossary_terms = set()
            if isinstance(extracted.get("glossary"), list):
                for g in extracted["glossary"]:
                    if isinstance(g, dict):
                        for term in g.keys():
                            if isinstance(term, str):
                                glossary_terms.add(term.lower())

            cleaned = []
            for s in extracted["stakeholders"]:
                if not isinstance(s, dict):
                    continue

                name = (s.get("name") or "").strip()
                if not name:
                    continue

                # لازم تكون كلمتين بالإنجليزي (First Last) - بسيطة
                if not re.fullmatch(r"[A-Za-z]+(?:\-[A-Za-z]+)?\s+[A-Za-z]+(?:\-[A-Za-z]+)?", name):
                    continue

                w1, w2 = [w.lower() for w in name.split()[:2]]

                # لو أي كلمة من كلمات الجهات/الأدوار => استبعد
                if (w1 in ORG_WORDS) or (w2 in ORG_WORDS):
                    continue

                # لو أي كلمة من الكلمات السيئة => استبعد
                if (w1 in BAD_TOKENS) or (w2 in BAD_TOKENS):
                    continue

                # لو الاسم جزء من مصطلح glossary (زي Customer Lifetime Value) => استبعد
                lower_name = name.lower()
                if any(lower_name in term for term in glossary_terms):
                    continue

                cleaned.append(s)

            extracted["stakeholders"] = cleaned

        return extracted
    def _guess_names(self, text: str):
        # نلقط أسماء من كلمتين (First Last) زي: "Sarah Ahmed"
        pairs = re.findall(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", text)

        # كلمات نطردها لو جات كأسماء
        stop_first = {"Project", "Meeting", "Transcript", "Strategic", "The", "January", "February", "March", "April"}
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

    # لو ما لقينا أي اسم من كلمتين، نرجع [] (ولا نخرب بالـ The و Strategic)
        return out

    def _guess_risks(self, text: str):
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