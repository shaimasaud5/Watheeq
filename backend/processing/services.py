import requests
import os, time
from groq import Groq

def simple_chunk(transcript, max_chars=300, overlap_lines=1):
    turns = transcript.get("turns", [])
    chunks = []
    current_chunk = []
    current_length = 0

    for turn in turns:
        speaker = turn.get("speaker", "Unknown")
        text = turn.get("text_clean", "")
        line = f"{speaker}: {text}"

        if len(line) > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            start = 0
            while start < len(line):
                end = start + max_chars
                chunks.append(line[start:end])
                start = end
            continue

        extra = len(line) + (1 if current_chunk else 0)

        if current_length + extra > max_chars:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                if overlap_lines > 0:
                    current_chunk = current_chunk[-overlap_lines:]
                else:
                    current_chunk = []
                current_length = len("\n".join(current_chunk))
            else:
                current_length = 0

        current_chunk.append(line)
        current_length = len("\n".join(current_chunk))

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def clean_semantic_output(text):
    text = text.strip()
    prefixes_to_remove = [
        "Here is the rewritten chunk in clear English:",
        "Here is the rewritten text:",
        "Rewritten text:",
        "Rewritten chunk:"
    ]
    for prefix in prefixes_to_remove:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    return text


def convert_chunk_to_semantic_english(text, model="llama-3.3-70b-versatile"):
    # url = "http://ollama:11434/api/generate"
    prompt = (
        "You are a translation engine, not an assistant.\n\n"

        "Your task:\n"
        "Translate and slightly refine Arabic-English meeting transcript lines into clear English.\n\n"

        "STRICT OUTPUT RULE:\n"
        "Your output MUST start directly with the first speaker line.\n"
        "Do NOT add any introduction, explanation, heading, or extra text.\n"
        "Do NOT write phrases like 'Here is the translated transcript' or anything similar.\n"
        "If you add any text before the first speaker line, your output is completely invalid.\n\n"

        "Rules:\n"
        "1. Return ONLY the translated speaker lines.\n"
        "2. Keep the exact format: Speaker: sentence\n"
        "3. Do NOT add headings, notes, or explanations.\n"
        "4. Do NOT summarize or remove information.\n"
        "5. Do NOT add new information.\n"
        "6. Preserve the meaning exactly.\n"
        "7. Do NOT merge or split speaker lines.\n"
        "8. Preserve questions as questions.\n\n"

        "Controlled rewriting:\n"
        "9. You may slightly improve sentence clarity.\n"
        "10. Do NOT change the intent or tone.\n"
        "11. Do NOT turn statements into questions or questions into statements.\n\n"

        "Consistency:\n"
        "12. If a line appears again, it MUST be translated the same way.\n"
        "13. Same input must produce the same output.\n\n"

        "Technical terms:\n"
        "14. Keep these exactly if they appear:\n"
        "webhook, API, ngrok, meeting link, transcript, chunk, chunks, embeddings, AI, pipeline, backend, frontend, BRD, MOM, Watheeq\n\n"

        "Translation rules:\n"
        "15. 'بوت' or 'bot' = bot\n"
        "16. Use 'webhook' ONLY if clearly mentioned\n"
        "17. 'وثيق' = Watheeq\n\n"

        "Natural phrases:\n"
        "18. 'يعطيك العافية' = Thank you\n"

        "FINAL WARNING:\n"
        "If you add any introduction or extra text, the output is wrong.\n"
        "Start immediately with the speaker lines.\n\n"

        "Transcript:\n"
        f"{text}"
    )

    client = Groq(api_key=os.getenv("GROQ_API_KEY_TASK2"))
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=600,
    )
    output = response.choices[0].message.content.strip()
    total_duration = time.time() - start
    if not total_duration :
        total_duration = None
    return output, model, total_duration


def generate_embeddings(texts, model="mxbai-embed-large"):
    url = "http://ollama:11434/api/embed"
    payload = {
        "model": model,
        "input": texts,
        "keep_alive": "10m"
    }
    r = requests.post(url, json=payload, timeout=(10, 300))
    r.raise_for_status()
    result = r.json()
    embeddings = result.get("embeddings", [])
    total_duration = result.get("total_duration")
    if total_duration:
        total_duration = total_duration / 1_000_000_000
    return embeddings, model, total_duration