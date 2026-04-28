# evaluation/evaluate.py

import json
from docx import Document
from rouge_score import rouge_scorer
from bert_score import score as bert_score

def flatten_json(obj, prefix="") -> str:
    """يحوّل الـ extracted_json لنص مسطّح للمقارنة"""
    parts = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            parts.append(flatten_json(v, prefix=k))
    elif isinstance(obj, list):
        for item in obj:
            parts.append(flatten_json(item))
    else:
        if obj:
            parts.append(str(obj).strip())
    return " ".join(parts)

def extract_docx_text(path: str) -> str:
    """يستخرج النص من الـ .docx المولّد"""
    doc = Document(path)
    return " ".join(p.text.strip() for p in doc.paragraphs if p.text.strip())

def evaluate(schema: dict, docx_path: str) -> dict:
    reference  = flatten_json(schema)
    hypothesis = extract_docx_text(docx_path)

    # ROUGE
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge  = scorer.score(reference, hypothesis)

    # BERTScore
    P, R, F1 = bert_score([hypothesis], [reference], lang="en")

    return {
        "rouge1_f":    round(rouge["rouge1"].fmeasure, 3),
        "rouge2_f":    round(rouge["rouge2"].fmeasure, 3),
        "rougeL_f":    round(rouge["rougeL"].fmeasure, 3),
        "bertscore_f": round(F1.mean().item(), 3),
    }
if __name__ == "__main__":
    import sys

    # كيفية الاستخدام:
    # python evaluate.py <path_to_schema.json> <path_to_generated.docx>

    if len(sys.argv) != 3:
        print("Usage: python evaluate.py schema.json document.docx")
        sys.exit(1)

    schema_path = sys.argv[1]
    docx_path   = sys.argv[2]

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    results = evaluate(schema, docx_path)

    print("\n===== Evaluation Results =====")
    print(f"ROUGE-1  : {results['rouge1_f']}")
    print(f"ROUGE-2  : {results['rouge2_f']}")
    print(f"ROUGE-L  : {results['rougeL_f']}")
    print(f"BERTScore: {results['bertscore_f']}")
    print("==============================\n")