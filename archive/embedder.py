import os
import json
import numpy as np
import faiss
from tqdm import tqdm
from openai import OpenAI

# === CONFIG ===
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_DIR = "data"
OUTPUT_INDEX_PATH = "data/embedding_index/faiss.index"
OUTPUT_METADATA_PATH = "data/embedding_index/metadata.json"
BATCH_SIZE = 100

# === Load API Key ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# === Helper functions ===
def load_chunks():
    text_chunks = []
    metadata = []
    for root, _, files in os.walk(CHUNK_DIR):
        for fname in files:
            if fname.endswith(".json"):
                path = os.path.join(root, fname)
                with open(path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        for chunk in data:
                            text_chunks.append(chunk["text"])
                            metadata.append({
                                "id": chunk["id"],
                                "source": chunk.get("source", path),
                                "file": fname,
                                "text": chunk["text"][:100]
                            })
                    except Exception as e:
                        print(f"⚠️ Skipping {path}: {e}")
    return text_chunks, metadata

def get_embeddings(texts):
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        response = client.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        batch_embeddings = [np.array(e.embedding, dtype=np.float32) for e in response.data]
        embeddings.extend(batch_embeddings)
    return np.vstack(embeddings)

def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index

def save_index(index, metadata):
    os.makedirs(os.path.dirname(OUTPUT_INDEX_PATH), exist_ok=True)
    faiss.write_index(index, OUTPUT_INDEX_PATH)
    with open(OUTPUT_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

# === Main ===
if __name__ == "__main__":
    print("🔍 Loading chunks...")
    texts, metadata = load_chunks()
    print(f"✅ Loaded {len(texts)} chunks")
    if not texts:
        print("❌ No chunks found. Please check your data/processed_chunks folder.")
        exit(1)

    print("🧠 Embedding...")
    embeddings = get_embeddings(texts)
    print("✅ Embedding complete")

    print("📦 Building index...")
    index = build_faiss_index(embeddings)

    print("💾 Saving index and metadata...")
    save_index(index, metadata)

    print("✅ All done.")
