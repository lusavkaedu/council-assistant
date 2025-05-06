
import os
import openai
import numpy as np

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_embeddings_batch(texts, model="text-embedding-3-small"):
    try:
        response = openai.embeddings.create(input=texts, model=model)
        return [d.embedding for d in response.data]
    except Exception as e:
        print(f"Embedding failed: {e}")
        return []

def save_faiss_index(index, metadata, index_path, metadata_path):
    import faiss
    faiss.write_index(index, index_path)
    with open(metadata_path, "w", encoding="utf-8") as f:
        import json
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def load_faiss_index(index_path, metadata_path):
    import faiss
    index = faiss.read_index(index_path)
    with open(metadata_path, "r", encoding="utf-8") as f:
        import json
        metadata = json.load(f)
    return index, metadata
