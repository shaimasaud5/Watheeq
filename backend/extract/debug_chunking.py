from embedding_service import generate_embedding
from retrieval_service import retrieve_top_chunks
from query_service import get_query_by_doc_type

# نحط doc_type
doc_type = "BRD"
# نجيب query بناء عليه
query = get_query_by_doc_type(doc_type)

query_embedding = generate_embedding(query)

#  retrieval
def get_top_k(chunks):
    if len(chunks) <= 3:
        return 2
    elif len(chunks) <= 6:
        return 4
    elif len(chunks) <= 10:
        return 7
    elif len(chunks) <= 20:
        return 14
    else:
        return 20
    
k = get_top_k(chunks_with_embeddings)
top_chunks = retrieve_top_chunks(query_embedding, chunks_with_embeddings,top_k=k )

print("\nTOP CHUNKS:")
for c in top_chunks:
    print("-", c)

clean_chunks = []

for c in top_chunks:
    if "sample transcript" in c.lower():
        continue
    if len(c.strip()) < 30:
        continue
    clean_chunks.append(c)


transcript = " ".join(clean_chunks)
transcript = transcript.replace('"', '')
transcript = transcript.replace('’', '')

print("\nFINAL TRANSCRIPT:")
print(transcript)

import requests

url = "http://backend:8000/api/extract-dynamic/"

payload = {
    "doc_type": doc_type,
    "transcript": transcript,
    "template_text": ""
}

response = requests.post(url, json=payload, timeout=300)

print("\nDYNAMIC STATUS:", response.status_code)
print("DYNAMIC RESPONSE:")
print(response.text)