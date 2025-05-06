
import os
import json
from app.utils.file_walker import find_all_chunks
from app.embeddings.embedder import get_embeddings_batch, save_faiss_index, load_faiss_index
import faiss
import numpy as np

INDEX_PATH = "data/embeddings/council_index.faiss"
METADATA_PATH = "data/embeddings/council_metadata.json"

existing_chunks = set()
if os.path.exists(METADATA_PATH):
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        existing_metadata = json.load(f)
    existing_chunks = set(m["source"] for m in existing_metadata)
    print(f"✅ Loaded {len(existing_chunks)} existing metadata entries.")
else:
    existing_metadata = []

texts, metadatas = [], []

for chunk_path in find_all_chunks():
    with open(chunk_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data or data[0]["source"] in existing_chunks:
        continue
    for chunk in data:
        texts.append(chunk["text"])
        metadatas.append({k: v for k, v in chunk.items() if k != "text"})

    embeddings = get_embeddings_batch(texts)
    if not embeddings:
        continue

    if os.path.exists(INDEX_PATH):
        index, existing_metadata = load_faiss_index(INDEX_PATH, METADATA_PATH)
    else:
        index = faiss.IndexFlatL2(len(embeddings[0]))

    index.add(np.array(embeddings).astype("float32"))
    existing_metadata.extend(metadatas)
    save_faiss_index(index, existing_metadata, INDEX_PATH, METADATA_PATH)
