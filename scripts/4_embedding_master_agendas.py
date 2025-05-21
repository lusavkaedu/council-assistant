# 4_embedding_master_agendas.py

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
import toml

# Load from Streamlit-style secrets
secrets = toml.load(".streamlit/secrets.toml")
OPENAI_API_KEY = secrets.get("OPENAI_API_KEY")

# === CONFIGURATION ===
EMBEDDING_TYPE = os.getenv("EMBEDDING_TYPE", "small")  # options: "small", "large"
EMBEDDING_MODEL = "text-embedding-3-small" if EMBEDDING_TYPE == "small" else "text-embedding-3-large"
EMBEDDING_DIM = 1536 if EMBEDDING_TYPE == "small" else 3072
BATCH_SIZE = 100
DOC_ID_REGISTER_PATH = "data/processed_register/document_ids.json"
OUTPUT_FAISS_PATH = "data/embeddings/agenda_index.faiss"
OUTPUT_METADATA_PATH = "data/embeddings/metadata_agenda.jsonl"
BATCH_METADATA_PATH = OUTPUT_METADATA_PATH  # same file
#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MANIFEST_PATH = "data/processed_register/agenda_manifest.jsonl"

def load_manifest(path: str):
    with open(path, "r") as f:
        return [json.loads(line) for line in f if line.strip()]

# === EMBEDDER CLASS ===
class Embedder:
    def __init__(self, model: str = EMBEDDING_MODEL, api_key: str = None):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed_batch(self, texts: List[str], attempt=1) -> List[List[float]]:
        if attempt > 5:
            raise RuntimeError("Too many retry attempts for embedding.")
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            print(f"Embedding error (attempt {attempt}): {e}")
            time.sleep(5)
            return self.embed_batch(texts, attempt=attempt + 1)

# === LOAD DOC ID REGISTER ===
def load_doc_id_register(path: str):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

# === FIND ALL CHUNK FILES ===
def find_all_chunk_files(base_dir: str, suffix: str):
    return glob.glob(os.path.join(base_dir, "**", f"*{suffix}"), recursive=True)

# === FILTERING FUNCTION ===
def is_meaningful(chunk):
    text = chunk.get("text", "").lower()
    title = chunk.get("item_title", "").lower()
    if len(text.split()) < 40:
        if any(k in text or k in title for k in [
            "apologies", "substitutes", "panel business", "motion to exclude",
            "minutes of the meeting", "future work programme", "webcast", "any other business"
        ]):
            return False
    return True

# === MAIN ===
def main():
    print("\n🔎 Starting embedding process...")
    embedder = Embedder(api_key=OPENAI_API_KEY)
    doc_id_register = load_doc_id_register(DOC_ID_REGISTER_PATH)
    manifest = load_manifest(MANIFEST_PATH)
    relevant_entries = [
        entry for entry in manifest
        if not entry.get(f"embedding_{EMBEDDING_TYPE}", False)
        and entry.get("text")
    ]
    print(f"Found {len(relevant_entries)} entries to embed")

    index = faiss.IndexFlatL2(EMBEDDING_DIM)

    batch_texts = [entry["text"] for entry in relevant_entries]
    batch_metadata = [
        {
            "doc_id": entry["doc_id"],
            "chunk_id": entry["chunk_id"],
            "text": entry["text"],
            "meeting_id": entry["meeting_id"],
            "committee_id": entry["committee_id"],
            "meeting_date": entry["meeting_date"],
            "source_type": entry.get("source_type", "agenda"),
        }
        for entry in relevant_entries
    ]

    for i in range(0, len(batch_texts), BATCH_SIZE):
        batch = batch_texts[i:i + BATCH_SIZE]
        try:
            embeddings = embedder.embed_batch(batch)
        except Exception as e:
            print(f"❌ Failed to embed batch: {e}")
            continue
        print(f"🟢 Embedded {len(embeddings)} items")

        index.add(np.array(embeddings).astype("float32"))

        with open(BATCH_METADATA_PATH, "a", encoding="utf-8") as meta_out:
            for j, embedding in enumerate(embeddings):
                chunk_meta = batch_metadata[i + j]
                meta_out.write(json.dumps(chunk_meta) + "\n")

    # Save FAISS index
    os.makedirs(os.path.dirname(OUTPUT_FAISS_PATH), exist_ok=True)
    faiss.write_index(index, OUTPUT_FAISS_PATH)
    print(f"✅ FAISS index saved to {OUTPUT_FAISS_PATH}")

    # Update manifest with embedding type fields
    updated_manifest = []
    for entry in manifest:
        if not entry.get(f"embedding_{EMBEDDING_TYPE}", False) and entry.get("text"):
            if EMBEDDING_TYPE == "small":
                entry["embedding_small"] = True
            elif EMBEDDING_TYPE == "large":
                entry["embedding_large"] = True
        updated_manifest.append(entry)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        for entry in updated_manifest:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"📦 Manifest updated: embedding_{EMBEDDING_TYPE} field written.")

if __name__ == "__main__":
    main()
