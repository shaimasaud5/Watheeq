import math

def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)

def retrieve_top_chunks(query_embedding, chunks_with_embeddings, top_k=3):
    scored_chunks = []

    for item in chunks_with_embeddings:
        chunk_text = item["semantic_english_text"]
        chunk_embedding = item["embedding"]

        score = cosine_similarity(query_embedding, chunk_embedding)

        scored_chunks.append((score, chunk_text))

    # ترتيب من الأعلى للأقرب
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # top_k
    top_chunks = [chunk for _, chunk in scored_chunks[:top_k]]

    return top_chunks