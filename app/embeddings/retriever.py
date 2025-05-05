
import faiss
import json
import numpy as np

INDEX_PATH = "data/embeddings/council_index.faiss"
METADATA_PATH = "data/embeddings/council_metadata.json"

def load_index_and_metadata():
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return index, metadata

def search_index(query_embedding, k=5):
    index, metadata = load_index_and_metadata()
    D, I = index.search(np.array([query_embedding]).astype("float32"), k)
    return [metadata[i] for i in I[0]]
