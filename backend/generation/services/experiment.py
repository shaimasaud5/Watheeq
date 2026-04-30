# experiment.py
# -----------------------------------------------------------------------
# Watheeq — Prompt & Model Comparison Experiment
#
# PURPOSE:
#   Compare 6 combinations of (prompt × model) across multiple schemas
#   to decide the best configuration for the final system.
#
# COMBINATIONS:
#   Prompt A = current few-shot prompt (baseline)
#   Prompt B = few-shot + ISO/IEC/IEEE 29148:2018 quality standards
#   Model 1  = Llama 3      (local via Ollama — free)
#   Model 2  = GPT-4        (via Azure OpenAI)
#   Model 3  = Claude Sonnet (via Anthropic API)
#
# USAGE:
#   1. Place your schema JSON files in the same folder as this script
#   2. Fill in your API keys in the CONFIG section below
#   3. Run: python experiment.py
#
# OUTPUT:
#   - experiment_outputs/       folder with all generated .docx files
#   - experiment_results.csv    all scores per combination
#   - experiment_report.txt     full summary with averages and recommendation
#
# ────────────────────────────────────────────────────────────────┘
# -----------------------------------------------------------------------

import os
import json
import time
import csv
import requests
from datetime import datetime
from docx import Document as DocxDocument
from rouge_score import rouge_scorer
from bert_score import score as bert_score_fn


# -----------------------------------------------------------------------
# CONFIG — EDIT THIS SECTION ONLY
# -----------------------------------------------------------------------

CONFIG = {

    # ── Llama 3 via Ollama (local, free) ──────────────────────────────
    "ollama_base_url":    "http://localhost:11434",  # change if needed
    "ollama_model":       "llama3",
    "ollama_temperature": 0.2,
    "ollama_timeout":     1200,  # 10 min: Llama loads model on first call

    # ── GPT-4 via Azure OpenAI ────────────────────────────────────────
    "azure_endpoint":     "https://rawad.openai.azure.com/",
    "azure_deployment":   "gpt-4",
    "azure_api_version":  "2024-12-01-preview",
    "azure_api_key":      "key",   # ← AZURE KEY HERE
    "azure_temperature":  0.2,
    "azure_timeout":      120,  # 2 min: GPT-4 is fast

    # ── Claude Sonnet via Anthropic API ───────────────────────────────
    "claude_api_key":     "key",  # ← CLAUDE KEY HERE
    "claude_model":       "claude-haiku-4-5-20251001",
    "claude_temperature": 0.2,
    "claude_timeout":     60,   # 1 min: Claude API is fast

    # ── Schemas to test ───────────────────────────────────────────────
    # Place all JSON files in the SAME FOLDER as this script.
    "schemas": [
        {"file": "schema_brd_1.json", "type": "BRD", "name": "BRD_1"},
        {"file": "schema_brd_2.json", "type": "BRD", "name": "BRD_2"},
        {"file": "schema_mom_1.json", "type": "MOM", "name": "MoM_1"},
        {"file": "schema_mom_2.json", "type": "MOM", "name": "MoM_2"},
    ],

    # ── Output folder ─────────────────────────────────────────────────
    "output_dir": "experiment_outputs",
}

# -----------------------------------------------------------------------
# END OF CONFIG — DO NOT EDIT BELOW
# -----------------------------------------------------------------------


# -----------------------------------------------------------------------
# PROMPTS
# -----------------------------------------------------------------------

_FEW_SHOT_EXAMPLES = """
EXAMPLE 1 — string field:
SECTION: Project Scope
DATA: The system will support user registration, product catalog, checkout, and order tracking. Out of scope: third-party logistics integration.
OUTPUT: The project encompasses the development of core e-commerce capabilities, including user registration, product catalog management, streamlined checkout, and real-time order tracking. Third-party logistics integration falls outside the defined project boundaries and will not be addressed in this release.

EXAMPLE 2 — list-of-strings field:
SECTION: Business Drivers
DATA: Increase conversion rate by 25%; Reduce cart abandonment by 20%; Improve page load speed to under 2 seconds
OUTPUT: The primary business objectives are to increase the platform conversion rate by 25% and reduce cart abandonment by 20%. Improving page load speed to under two seconds is a key performance target to enhance user experience and support revenue growth.

EXAMPLE 3 — field containing priority data:
SECTION: Performance Requirements
DATA: priority: high; category: performance; description: system must handle 10,000 concurrent users
OUTPUT: A high-priority performance requirement mandates that the system support a minimum of 10,000 concurrent users without degradation in response time. This ensures the platform remains stable and responsive during peak traffic periods.

EXAMPLE 4 — BAD vs GOOD (study carefully):
DATA: The platform must support Arabic and English languages.
BAD: Here is the section on language support: The platform must support Arabic and English. (starts with preamble)
GOOD: The platform is required to support both Arabic and English languages, ensuring accessibility for the target user base across the region.
""".strip()

_STRICT_RULES = """
STRICT RULES:
1. Output ONLY the sentences. Nothing else — no title, no label, no preamble.
2. Do NOT start with "Here is", "Sure", "Certainly", "This section", "Based on", "The following", or any introduction phrase.
3. Do NOT add any information that is not in DATA above.
4. Do NOT use bullet points, numbered lists, or dashes.
5. Write in formal business English only.
6. Do NOT repeat the section name in your output.
7. End with a period.
8. Priority levels MUST be expressed as "High", "Medium", or "Low" only.
   NEVER use "must", "should", "could", or any MoSCoW term as a priority label.
"""

_ISO_QUALITY_BLOCK = """
QUALITY STANDARD (ISO/IEC/IEEE 29148:2018):
Apply these four principles to every sentence you write:

UNAMBIGUOUS — use precise, measurable language.
  Avoid vague terms: "fast", "efficient", "user-friendly", "reliable", "good", "easy"
  Use instead: specific numbers, conditions, and outcomes.
  Wrong: "the system shall respond quickly"
  Right: "the system shall respond within 2 seconds under a standard 4G connection"

COMPLETE — include who, what, under what conditions, and the expected outcome.
  Do not leave the reader needing additional information.

SINGULAR — express exactly one capability or constraint per sentence.
  Wrong: "Users can register, login, and manage their profile"
  Right: "Users can register using their mobile number with OTP verification"

VERIFIABLE — every claim must be testable or measurable.
  Preserve all numbers and thresholds from the DATA exactly.

TRACEABLE — every statement must come directly from the DATA provided.
  Do not add assumptions or external knowledge not present in the DATA.
"""


def build_prompt_a(section_label: str, raw_text: str) -> str:
    """Prompt A — few-shot only (current system baseline)."""
    return f"""You are a senior business analyst writing one section of a formal document.
Study these examples of correct output style before writing:

{_FEW_SHOT_EXAMPLES}

---
Now write the section below using the same style.

SECTION: {section_label}
DATA: {raw_text}

Write as many sentences as needed to cover all the DATA above — no more, no less.

{_STRICT_RULES}

OUTPUT:"""


def build_prompt_b(section_label: str, raw_text: str) -> str:
    """Prompt B — few-shot + ISO/IEC/IEEE 29148:2018 quality standards."""
    return f"""You are a senior business analyst writing one section of a formal document.
Your output must conform to ISO/IEC/IEEE 29148:2018 requirements engineering quality standards.

{_ISO_QUALITY_BLOCK}

Study these examples of correct output style before writing:

{_FEW_SHOT_EXAMPLES}

---
Now write the section below using the same style AND the quality standards above.

SECTION: {section_label}
DATA: {raw_text}

Write as many sentences as needed to cover all the DATA above — no more, no less.

{_STRICT_RULES}

OUTPUT:"""


# -----------------------------------------------------------------------
# MODEL CLIENTS
# -----------------------------------------------------------------------

class LlamaClient:
    """
    Calls Ollama REST API directly (no LangChain).
    Free — runs locally on your machine.
    Timeout 600s because the first call loads the model (~3-5 min).
    """
    def __init__(self, cfg):
        self.base_url    = cfg["ollama_base_url"]
        self.model       = cfg["ollama_model"]
        self.temperature = cfg["ollama_temperature"]
        self.timeout     = cfg["ollama_timeout"]

    def generate(self, prompt):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": self.temperature, "num_predict": 600},
        }
        t0 = time.time()
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            text = r.json().get("response", "").strip()
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Llama timed out ({self.timeout}s). Is Ollama running?")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Cannot connect to Ollama at {self.base_url}")
        return text, round(time.time() - t0, 2)


class GPT4Client:
    """
    Calls Azure OpenAI GPT-4.
    Timeout 120s — GPT-4 is fast, main risk is network latency.
    Key: CONFIG['azure_api_key']
    """
    def __init__(self, cfg):
        self.endpoint    = cfg["azure_endpoint"].rstrip("/")
        self.deployment  = cfg["azure_deployment"]
        self.api_version = cfg["azure_api_version"]
        self.api_key     = cfg["azure_api_key"]
        self.temperature = cfg["azure_temperature"]
        self.timeout     = cfg["azure_timeout"]

    def generate(self, prompt):
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}"
            f"/chat/completions?api-version={self.api_version}"
        )
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        payload = {
            "messages": [
                {"role": "system", "content": "You are a senior business analyst."},
                {"role": "user",   "content": prompt},
            ],
            "temperature": self.temperature, "max_tokens": 600,
        }
        t0 = time.time()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            raise RuntimeError(f"GPT-4 timed out ({self.timeout}s)")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Azure OpenAI")
        except KeyError:
            raise RuntimeError(f"Unexpected Azure response: {r.text[:300]}")
        return text, round(time.time() - t0, 2)


class ClaudeClient:
    """
    Calls Anthropic Claude API directly.
    Timeout 60s — Claude API is fast and reliable.
    Key: CONFIG['claude_api_key']

    Cost: ~$0.011 per document.
    Full experiment (8 docs): ~$0.09 total.
    Get key: https://console.anthropic.com → API Keys → Create Key
    """
    def __init__(self, cfg):
        self.api_key     = cfg["claude_api_key"]
        self.model       = cfg["claude_model"]
        self.temperature = cfg["claude_temperature"]
        self.timeout     = cfg["claude_timeout"]
        self.url         = "https://api.anthropic.com/v1/messages"

    def generate(self, prompt):
        headers = {
            "x-api-key":         self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        payload = {
            "model": self.model, "max_tokens": 600,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        t0 = time.time()
        try:
            r = requests.post(self.url, headers=headers, json=payload, timeout=self.timeout)
            r.raise_for_status()
            text = r.json()["content"][0]["text"].strip()
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Claude timed out ({self.timeout}s)")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Cannot connect to Anthropic API")
        except Exception as e:
            raise RuntimeError(f"Claude full error: {r.status_code} — {r.text}")
        return text, round(time.time() - t0, 2)


# -----------------------------------------------------------------------
# TEXT HELPERS
# -----------------------------------------------------------------------

_PREAMBLE_STARTS = (
    "here is", "here's", "sure,", "sure!", "certainly,", "of course",
    "this section", "below is", "the following", "as requested",
    "based on", "i will", "i'll", "please find", "in this section",
    "this document", "the document", "note:", "note that", "as a senior",
)

_ACRONYMS = {
    "kpis": "KPIs", "kpi": "KPI", "id": "ID", "brd": "BRD",
    "mom": "MoM", "srs": "SRS", "ui": "UI", "ux": "UX",
    "api": "API", "url": "URL", "aov": "AOV", "ai": "AI",
    "it": "IT", "hr": "HR",
}


def clean_llm_output(text):
    cleaned = []
    for line in text.strip().splitlines():
        s = line.strip()
        if not s: continue
        if s.startswith("#"): continue
        if set(s).issubset(set("-=_ ")): continue
        if any(s.lower().startswith(p) for p in _PREAMBLE_STARTS): continue
        cleaned.append(s)
    return " ".join(cleaned).strip()


def key_to_label(key):
    return " ".join(_ACRONYMS.get(w.lower(), w.capitalize()) for w in key.split("_"))


def value_to_raw_text(value):
    if value is None: return ""
    if isinstance(value, str): return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(", ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if isinstance(v, list):
                parts.append(f"{k}: {', '.join(str(i) for i in v)}")
            elif isinstance(v, dict):
                parts.append(f"{k}: {', '.join(str(x) for x in v.values())}")
            else:
                parts.append(f"{k}: {v}")
        return "; ".join(parts)
    return str(value)


def is_structural(value):
    return isinstance(value, dict) or (isinstance(value, list) and len(value) > 0)


def dict_has_string_values(d):
    return any(isinstance(v, str) and str(v).strip() for v in d.values())


def flatten_json(obj):
    parts = []
    if isinstance(obj, dict):
        for v in obj.values(): parts.append(flatten_json(v))
    elif isinstance(obj, list):
        for item in obj: parts.append(flatten_json(item))
    else:
        if obj: parts.append(str(obj).strip())
    return " ".join(p for p in parts if p)


# -----------------------------------------------------------------------
# DOCUMENT GENERATION
# -----------------------------------------------------------------------

_ALWAYS_STRUCTURAL = {"document_control", "meeting_info"}


def generate_document(schema, prompt_fn, model_client, doc_type):
    sections, per_field_times, total_elapsed = [], {}, 0.0

    for field_key, field_value in schema.items():
        if field_value in (None, "", [], {}):
            continue

        label    = key_to_label(field_key)
        raw_text = value_to_raw_text(field_value)

        # Case 1: always structural
        if field_key in _ALWAYS_STRUCTURAL:
            sections.append(f"\n{label}\n{raw_text}")
            continue

        # Case 2: dict with string sub-values (e.g. executive_summary from girl 3)
        if isinstance(field_value, dict) and dict_has_string_values(field_value):
            sub_lines = [f"\n{label}"]
            for sub_key, sub_val in field_value.items():
                if not sub_val or not isinstance(sub_val, str):
                    sub_lines.append(f"  {key_to_label(sub_key)}: {value_to_raw_text(sub_val)}")
                    continue
                sub_label = key_to_label(sub_key)
                prompt    = prompt_fn(sub_label, value_to_raw_text(sub_val))
                t0        = time.time()
                raw, _    = model_client.generate(prompt)
                elapsed   = round(time.time() - t0, 2)
                prose     = clean_llm_output(raw)
                if len(prose) < 10: prose = sub_val
                sub_lines.append(f"  {sub_label}: {prose}")
                per_field_times[f"{field_key}.{sub_key}"] = elapsed
                total_elapsed += elapsed
            sections.append("\n".join(sub_lines))
            continue

        # Case 3: structural list/dict → render as-is
        if is_structural(field_value):
            sections.append(f"\n{label}\n{raw_text}")
            continue

        # Case 4: plain string → LLM prose
        prompt  = prompt_fn(label, raw_text)
        t0      = time.time()
        raw, _  = model_client.generate(prompt)
        elapsed = round(time.time() - t0, 2)
        prose   = clean_llm_output(raw)
        if len(prose) < 10: prose = raw_text
        sections.append(f"\n{label}\n{prose}")
        per_field_times[field_key] = elapsed
        total_elapsed += elapsed

    return "\n".join(sections), round(total_elapsed, 2), per_field_times


# -----------------------------------------------------------------------
# EVALUATION
# -----------------------------------------------------------------------

def evaluate_scores(reference, hypothesis):
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge  = scorer.score(reference, hypothesis)
    _, _, F1 = bert_score_fn([hypothesis], [reference], lang="en", verbose=False)
    return {
        "rouge1":    round(rouge["rouge1"].fmeasure, 3),
        "rouge2":    round(rouge["rouge2"].fmeasure, 3),
        "rougeL":    round(rouge["rougeL"].fmeasure, 3),
        "bertscore": round(F1.mean().item(),          3),
    }


def save_docx(text, path):
    doc = DocxDocument()
    for line in text.splitlines():
        if line.strip(): doc.add_paragraph(line.strip())
    doc.save(path)


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------

def run_experiment():
    cfg = CONFIG
    os.makedirs(cfg["output_dir"], exist_ok=True)

    prompts = {"A_baseline": build_prompt_a, "B_iso29148": build_prompt_b}
    models  = {
        "Llama3": LlamaClient(cfg),
        "GPT4":   GPT4Client(cfg),
        "Claude": ClaudeClient(cfg),
    }

    schemas = []
    for s in cfg["schemas"]:
        if not os.path.exists(s["file"]):
            print(f"  [SKIP] Not found: {s['file']}")
            continue
        with open(s["file"], "r", encoding="utf-8") as f:
            schemas.append({"data": json.load(f), "doc_type": s["type"], "name": s["name"]})

    if not schemas:
        print("No schema files found. Check CONFIG['schemas'].")
        return

    total = len(schemas) * len(prompts) * len(models)
    n_api = len(schemas) * len(prompts)
    print(f"\n{'='*68}")
    print(f"  Watheeq Experiment — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Schemas:{len(schemas)}  Prompts:{len(prompts)}  Models:{len(models)}  Total:{total}")
    print(f"  Est. cost — GPT-4:~${n_api*0.05:.2f}  Claude:~${n_api*0.011:.2f}  Llama:$0.00")
    print(f"{'='*68}\n")

    all_results, combo_num = [], 0

    for schema_info in schemas:
        reference = flatten_json(schema_info["data"])
        for prompt_name, prompt_fn in prompts.items():
            for model_name, model_client in models.items():
                combo_num += 1
                print(f"[{combo_num}/{total}] {schema_info['name']:<10} | {model_name:<7} | Prompt {prompt_name}")
                print("  Generating ...", end=" ", flush=True)

                try:
                    t0 = time.time()
                    text, gen_time, _ = generate_document(
                        schema_info["data"], prompt_fn, model_client, schema_info["doc_type"]
                    )
                    print(f"done in {round(time.time()-t0, 1)}s")

                    safe = f"{schema_info['name']}_{model_name}_Prompt{prompt_name}"
                    docx_path = os.path.join(cfg["output_dir"], f"{safe}.docx")
                    save_docx(text, docx_path)

                    print("  Evaluating ...", end=" ", flush=True)
                    scores = evaluate_scores(reference, text)
                    print(f"R-1={scores['rouge1']}  R-L={scores['rougeL']}  BERT={scores['bertscore']}")

                    all_results.append({
                        "schema": schema_info["name"], "doc_type": schema_info["doc_type"],
                        "model": model_name, "prompt": prompt_name,
                        **scores, "gen_time_s": gen_time,
                        "docx_file": docx_path, "status": "OK",
                    })

                except Exception as exc:
                    print(f"FAILED — {exc}")
                    all_results.append({
                        "schema": schema_info["name"], "doc_type": schema_info["doc_type"],
                        "model": model_name, "prompt": prompt_name,
                        "rouge1": None, "rouge2": None, "rougeL": None,
                        "bertscore": None, "gen_time_s": None,
                        "docx_file": None, "status": f"ERROR: {exc}",
                    })
                print()

    # Save CSV
    csv_path = "experiment_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "schema","doc_type","model","prompt",
            "rouge1","rouge2","rougeL","bertscore",
            "gen_time_s","docx_file","status"
        ])
        writer.writeheader()
        writer.writerows(all_results)
    print(f"\nCSV  saved → {csv_path}")

    _print_summary(all_results)
    _save_report(all_results)


def _print_summary(results):
    ok = [r for r in results if r["status"] == "OK"]
    if not ok:
        print("\nNo successful results.")
        return

    print(f"\n{'='*78}")
    print("  INDIVIDUAL RESULTS")
    print(f"{'='*78}")
    print(f"{'Schema':<12} {'Model':<8} {'Prompt':<12} {'R-1':>6} {'R-2':>6} {'R-L':>6} {'BERT':>7} {'Time':>7}")
    print("-"*78)
    for r in ok:
        print(f"{r['schema']:<12} {r['model']:<8} {r['prompt']:<12} "
              f"{r['rouge1']:>6.3f} {r['rouge2']:>6.3f} {r['rougeL']:>6.3f} "
              f"{r['bertscore']:>7.3f} {r['gen_time_s']:>6.1f}s")

    print(f"\n{'─'*78}")
    print("  AVERAGES BY COMBINATION  (sorted best → worst)")
    print(f"{'─'*78}")

    combos = {}
    for r in ok:
        key = f"{r['model']:<7} | Prompt {r['prompt']}"
        combos.setdefault(key, []).append(r)

    rows = []
    for key, rlist in combos.items():
        n = len(rlist)
        r1 = round(sum(x["rouge1"]    for x in rlist)/n, 3)
        r2 = round(sum(x["rouge2"]    for x in rlist)/n, 3)
        rl = round(sum(x["rougeL"]    for x in rlist)/n, 3)
        b  = round(sum(x["bertscore"] for x in rlist)/n, 3)
        t  = round(sum(x["gen_time_s"]for x in rlist)/n, 1)
        rows.append((key, r1, r2, rl, b, t, round((rl+b)/2, 3)))

    rows.sort(key=lambda x: x[6], reverse=True)

    print(f"{'Combination':<26} {'Avg R-1':>8} {'Avg R-2':>8} {'Avg R-L':>8} {'Avg BERT':>9} {'Time':>7} {'Score':>7}")
    print("-"*78)
    for i, (key, r1, r2, rl, b, t, score) in enumerate(rows):
        marker = "  ← BEST" if i == 0 else ""
        print(f"{key:<26} {r1:>8.3f} {r2:>8.3f} {rl:>8.3f} {b:>9.3f} {t:>6.1f}s {score:>7.3f}{marker}")

    print(f"\n  ★ Recommended: {rows[0][0].strip()}")
    print(f"  Score = (Avg ROUGE-L + Avg BERTScore) / 2 = {rows[0][6]}")
    print(f"{'='*78}\n")


def _save_report(results):
    ok = [r for r in results if r["status"] == "OK"]
    lines = [
        "="*80, "WATHEEQ — EXPERIMENT REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "="*80, "", "INDIVIDUAL RESULTS", "-"*80,
    ]
    for r in results:
        block = (f"Schema: {r['schema']} ({r['doc_type']})  |  "
                 f"Model: {r['model']}  |  Prompt: {r['prompt']}\n"
                 f"Status: {r['status']}\n")
        if r["status"] == "OK":
            block += (f"ROUGE-1:{r['rouge1']}  ROUGE-2:{r['rouge2']}  "
                      f"ROUGE-L:{r['rougeL']}  BERTScore:{r['bertscore']}  "
                      f"Time:{r['gen_time_s']}s\n"
                      f"File: {r['docx_file']}\n")
        lines.append(block + "-"*40)

    if ok:
        combos = {}
        for r in ok:
            key = f"{r['model']} | Prompt {r['prompt']}"
            combos.setdefault(key, []).append(r)
        rows = []
        for key, rlist in combos.items():
            n  = len(rlist)
            r1 = round(sum(x["rouge1"]    for x in rlist)/n, 3)
            r2 = round(sum(x["rouge2"]    for x in rlist)/n, 3)
            rl = round(sum(x["rougeL"]    for x in rlist)/n, 3)
            b  = round(sum(x["bertscore"] for x in rlist)/n, 3)
            t  = round(sum(x["gen_time_s"]for x in rlist)/n, 1)
            rows.append((key, r1, r2, rl, b, t, round((rl+b)/2, 3)))
        rows.sort(key=lambda x: x[6], reverse=True)

        lines += ["", "AVERAGES BY COMBINATION (best → worst)", "-"*80]
        for i, (key, r1, r2, rl, b, t, score) in enumerate(rows):
            marker = "  ← BEST" if i == 0 else ""
            lines.append(
                f"{key}{marker}\n"
                f"  ROUGE-1:{r1}  ROUGE-2:{r2}  ROUGE-L:{rl}  "
                f"BERTScore:{b}  Time:{t}s  Score:{score}\n"
            )
        lines += [
            "-"*80,
            f"RECOMMENDATION: {rows[0][0].strip()}",
            f"Score = (ROUGE-L + BERTScore) / 2 = {rows[0][6]}",
            "="*80,
        ]

    report_path = "experiment_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Report saved → {report_path}\n")


if __name__ == "__main__":
    run_experiment()