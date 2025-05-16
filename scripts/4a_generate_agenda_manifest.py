import json
from pathlib import Path

INPUT_CHUNKS_PATH = Path("data/chunks/minutes/chunks.jsonl")
MANIFEST_PATH = Path("data/processed_register/document_manifest.jsonl")
CHUNK_SOURCE_TYPE = "agenda"
CHUNK_PATH = str(INPUT_CHUNKS_PATH)

# Keywords to identify low-value items
low_signal_keywords = [
    "apologies", "substitutes", "panel business",
    "motion to exclude", "minutes of the meeting",
    "future work programme", "webcast", "any other business"
]

def is_meaningful(chunk):
    text = chunk.get("text", "").strip().lower()
    title = chunk.get("item_title", "").strip().lower()
    if len(text.split()) < 40:
        if any(k in text or k in title for k in low_signal_keywords):
            return False
    return True

# Load all meaningful agenda chunks
with open(INPUT_CHUNKS_PATH, "r", encoding="utf-8") as f:
    meaningful_chunks = [
        json.loads(line) for line in f if is_meaningful(json.loads(line))
    ]

# Group by meeting_code and meeting_date to build doc_ids
grouped = {}
for chunk in meaningful_chunks:
    code = chunk["meeting_code"]
    date = chunk["meeting_date"]
    key = f"{date}_{code}"
    grouped[key] = {
        "doc_id": f"webscrape_{date}_{code}",
        "chunk_path": CHUNK_PATH,
        "source_type": CHUNK_SOURCE_TYPE,
        "status": "ready_for_embedding",
        "embedding_small": False,
        "embedding_large": False
    }

# Load existing manifest doc_ids to avoid duplicates
existing_doc_ids = set()
if MANIFEST_PATH.exists():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                existing_doc_ids.add(entry.get("doc_id"))
            except:
                continue

# Append only new entries
#with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
#    for item in grouped.values():
#        if item["doc_id"] not in existing_doc_ids:
#            f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"✅ Added {len([i for i in grouped.values() if i['doc_id'] not in existing_doc_ids])} new agenda manifest entries.")