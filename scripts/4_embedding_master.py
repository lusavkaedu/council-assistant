# embed_all_chunks.py

import os
import json
import glob
import time
import faiss
import tiktoken
import numpy as np
from tqdm import tqdm
from openai import OpenAI
from typing import List

# === CONFIGURATION ===
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072
BATCH_SIZE = 100
BASE_DIR = "data/processed_chunks"
CHUNK_SUFFIX = "_chunks.json"
DOC_ID_REGISTER_PATH = "data/doc_id_register.json"
OUTPUT_FAISS_PATH = "data/embeddings/council_index_large.faiss"
OUTPUT_METADATA_PATH = "data/embeddings/metadata_large.jsonl"
BATCH_METADATA_PATH = OUTPUT_METADATA_PATH  # same file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MANIFEST_PATH = "data/processed_register/document_manifest.jsonl"

def load_manifest(path: str):
    with open(path, "r") as f:
        return [json.loads(line) for line in f if line.strip()]

# === EMBEDDER CLASS ===
class Embedder:
    def __init__(self, model: str = EMBEDDING_MODEL, api_key: str = None):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            print("Embedding error:", e)
            time.sleep(5)
            return self.embed_batch(texts)

# === LOAD DOC ID REGISTER ===
def load_doc_id_register(path: str):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

# === FIND ALL CHUNK FILES ===
def find_all_chunk_files(base_dir: str, suffix: str):
    return glob.glob(os.path.join(base_dir, "**", f"*{suffix}"), recursive=True)

# === MAIN ===
def main():
    print("\n🔎 Starting embedding process...")
    embedder = Embedder(api_key=OPENAI_API_KEY)
    doc_id_register = load_doc_id_register(DOC_ID_REGISTER_PATH)
    manifest = load_manifest(MANIFEST_PATH)
    relevant_entries = [
        entry for entry in manifest
        if entry.get("chunk_path")
        and entry.get("doc_id")
        and entry.get("status") == "embedded"
        and not entry.get("embedding_large")
    ]

    index = faiss.IndexFlatL2(EMBEDDING_DIM)

    for entry in tqdm(relevant_entries):
        chunk_path = entry["chunk_path"]
        doc_id = entry["doc_id"]
        relative_path = entry["relative_path"]

        with open(chunk_path, "r") as f:
            chunks = json.load(f)

        texts = [c["text"] for c in chunks if "text" in c]
        chunk_ids = list(range(len(texts)))

        for i in range(0, min(len(texts), 2), BATCH_SIZE):  # Limit to 2 entries for test
            batch = [t for t in texts[i:i + BATCH_SIZE] if t and t.strip()]
            if not batch:
                print(f"⚠️ Skipping empty or invalid batch in {relative_path}")
                continue

            embeddings = embedder.embed_batch(batch)
            index.add(np.array(embeddings).astype("float32"))

            with open(BATCH_METADATA_PATH, "a", encoding="utf-8") as meta_out:
                for j, embedding in enumerate(embeddings):
                    entry = {
                        "doc_id": doc_id,
                        "chunk_id": i + j,
                        "text": batch[j],
                        "source_file": relative_path
                    }
                    meta_out.write(json.dumps(entry) + "\n")

    # Save FAISS index
    os.makedirs(os.path.dirname(OUTPUT_FAISS_PATH), exist_ok=True)
    faiss.write_index(index, OUTPUT_FAISS_PATH)
    print(f"✅ FAISS index saved to {OUTPUT_FAISS_PATH}")

    # Update manifest with embedding_large field
    updated_manifest = []
    for entry in manifest:
        if entry.get("status") == "ready_for_embedding" and entry.get("doc_id") and entry.get("chunk_path"):
            entry["embedding_large"] = True
        updated_manifest.append(entry)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        for entry in updated_manifest:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("📦 Manifest updated: embedding_large field written.")

if __name__ == "__main__":
    main()
