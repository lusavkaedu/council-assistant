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
EMBEDDING_TYPE = os.getenv("EMBEDDING_TYPE", "small")  # options: "small", "large"
EMBEDDING_MODEL = "text-embedding-3-small" if EMBEDDING_TYPE == "small" else "text-embedding-3-large"
EMBEDDING_DIM = 1536 if EMBEDDING_TYPE == "small" else 3072
BATCH_SIZE = 100
BASE_DIR = "data/processed_chunks"
CHUNK_SUFFIX = "_chunks.json"
DOC_ID_REGISTER_PATH = "data/processed_register/document_ids.json"
OUTPUT_FAISS_PATH = f"data/embeddings/council_index_{EMBEDDING_TYPE}.faiss"
OUTPUT_METADATA_PATH = f"data/embeddings/metadata_{EMBEDDING_TYPE}.jsonl"
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
    RESET_EMBEDDINGS = os.getenv("RESET_EMBEDDINGS", "false").lower() == "true"
    relevant_entries = [
        entry for entry in manifest
        if entry.get("chunk_path")
        and entry.get("doc_id")
        and entry.get("status") == "ready_for_embedding"
        and (RESET_EMBEDDINGS or not entry.get(f"embedding_{EMBEDDING_TYPE}"))
    ]
    print(f"Found {len(relevant_entries)} entries to embed")

    index = faiss.IndexFlatL2(EMBEDDING_DIM)

    for entry in tqdm(relevant_entries, desc="📌 Embedding entries"):
        chunk_path = entry["chunk_path"]
        doc_id = entry["doc_id"]

        with open(chunk_path, "r") as f:
            chunks = json.load(f)

        valid_chunks = [c for c in chunks if all(k in c for k in ("text",))]
        if len(valid_chunks) < len(chunks):
            print(f"⚠️ Skipping {len(chunks) - len(valid_chunks)} incomplete chunks in {chunk_path}")

        batch_texts = []
        batch_metadata = []

        for c in valid_chunks:
            text = c["text"]
            if text and text.strip():
                batch_texts.append(text)
                batch_metadata.append({
                    "doc_id": doc_id,
                    "text": text,
                    "source_file": chunk_path,
                    "committee": doc_id_register.get(doc_id, {}).get("committee", "N/A"),
                    "meeting_date": doc_id_register.get(doc_id, {}).get("meeting_date", "N/A"),
                })

        for i in range(0, len(batch_texts), BATCH_SIZE):
            batch = batch_texts[i:i + BATCH_SIZE]
            if not batch:
                continue
            embeddings = embedder.embed_batch(batch)
            index.add(np.array(embeddings).astype("float32"))

            with open(BATCH_METADATA_PATH, "a", encoding="utf-8") as meta_out:
                for j, embedding in enumerate(embeddings):
                    chunk_meta = batch_metadata[i + j].copy()
                    chunk_meta["chunk_id"] = i + j  # doc-level chunk index
                    meta_out.write(json.dumps(chunk_meta) + "\n")

    # Save FAISS index
    os.makedirs(os.path.dirname(OUTPUT_FAISS_PATH), exist_ok=True)
    faiss.write_index(index, OUTPUT_FAISS_PATH)
    print(f"✅ FAISS index saved to {OUTPUT_FAISS_PATH}")

    # Update manifest with embedding type fields
    updated_manifest = []
    for entry in manifest:
        if entry.get("status") == "ready_for_embedding" and entry.get("doc_id") and entry.get("chunk_path"):
            if EMBEDDING_TYPE == "small":
                entry["embedding_small"] = True
            elif EMBEDDING_TYPE == "large":
                entry["embedding_large"] = True
            else:
                entry["embedding_small"] = entry.get("embedding_small", False)
                entry["embedding_large"] = entry.get("embedding_large", False)
        updated_manifest.append(entry)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        for entry in updated_manifest:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"📦 Manifest updated: embedding_{EMBEDDING_TYPE} field written.")

if __name__ == "__main__":
    main()
