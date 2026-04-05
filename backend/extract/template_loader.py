import json
from pathlib import Path


def load_template_from_json_file(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {file_path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def extract_text_from_file(file):
    filename = file.name.lower()

    # PDF
    if filename.endswith(".pdf"):
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    # DOCX
    elif filename.endswith(".docx"):
        import docx
        doc = docx.Document(file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

    else:
        raise ValueError("Unsupported file type. Only PDF and DOCX are allowed.")