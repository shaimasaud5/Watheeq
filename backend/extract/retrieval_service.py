# extract/retrieval_service.py
# ─────────────────────────────
# يحسب التشابه بين embedding اسم الفقرة وكل chunk embeddings
# ويرجع أعلى top_k chunks تشابهاً.

import math


def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    يحسب التشابه بين vectorين.
    النتيجة بين 0 (لا تشابه) و1 (تطابق كامل).
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot   = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def retrieve_top_chunks(section_embedding: list, chunks: list, top_k: int = 3) -> list:
    """
    يقارن embedding اسم الفقرة بكل chunk embeddings المحفوظة من مهمة 2.
    يرجع أعلى top_k chunks تشابهاً كقائمة نصوص.

    chunks: قائمة من {"semantic_english_text": str, "embedding": list}
    """
    scored = []
    for chunk in chunks:
        score = cosine_similarity(section_embedding, chunk["embedding"])
        scored.append((score, chunk["semantic_english_text"]))

    # ترتيب من الأعلى تشابهاً للأقل
    scored.sort(key=lambda x: x[0], reverse=True)

    return [text for _, text in scored[:top_k]]
