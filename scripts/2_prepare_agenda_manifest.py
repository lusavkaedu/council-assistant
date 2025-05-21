#scripts/2_prepare_agenda_manifest.py
# the filters applied in the script are based on the detailed examination performed in the notebook:
# notebooks/EDA_agenda_items_detailed_analysis.ipynb

import pandas as pd
import hashlib
from pathlib import Path
import json

# === Paths ===
SOURCE = Path("data/metadata/agendas.jsonl")
DEST = Path("data/processed_register/agenda_manifest.jsonl")
DEST.parent.mkdir(parents=True, exist_ok=True)

# === Load Data ===
df = pd.read_json(SOURCE, lines=True)

# === Junk Filter Logic ===
def looks_like_junk(row):
    text = str(row["item_text"]).lower()
    wc = row["word_count"]
    category = row["category"]

    junk_patterns = ["webcast", "view the reasons why", "additional documents", "see minute"]
    if any(p in text for p in junk_patterns):
        return True

    if category == "appeal":
        return True

    if wc < 20:
        return True

    name_triggers = ["mr ", "ms ", "mrs ", "dr ", "miss "]

    if category == "declarations":
        if wc < 30 and not any(p in text for p in name_triggers):
            return True

    if category == "questions":
        if wc < 30 and not any(p in text for p in name_triggers):
            return True

    return False

# === Embed Filter Logic ===
def assign_embed_status(row):
    category = row["category"]
    wc = row["word_count"]
    text = str(row["item_text"]).lower()
    has_pdf = isinstance(row.get("pdf_urls"), list) and len(row["pdf_urls"]) > 0
    is_junk = row.get("junk_flag", False)

    if is_junk:
        return False

    if category == "discussion":
        return wc > 10

    if category == "work_programme":
        return wc > 10

    if category == "questions":
        return wc > 30 or has_pdf

    if category == "appeal":
        return wc > 10 or "restricted" in text

    if category == "appointments":
        return wc > 20

    if category == "declarations":
        return wc > 50

    return False

# === Apply Filters ===
df["junk_flag"] = df.apply(looks_like_junk, axis=1)
df["embed_status"] = df.apply(assign_embed_status, axis=1)

# === Filter to embeddable items ===
chunks = df[df["embed_status"]].copy()

# === Prepare Manifest Entries ===
def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

manifest_entries = []

for _, row in chunks.iterrows():
    full_text = f"{row['item_title']}\n\n{row['item_text']}".strip()
    entry = {
        "chunk_id": row["agenda_id"],
        "doc_id": f"agenda_{row['agenda_id']}",
        "meeting_id": row["meeting_id"],
        "committee_id": row["committee_id"],
        "meeting_date": row["meeting_date"],
        "source_type": "agenda",
        "text": full_text,
        "text_hash": hash_text(full_text),
        "embedding_small": False
    }
    manifest_entries.append(entry)

# === Write to JSONL ===
with open(DEST, "w") as f:
    for item in manifest_entries:
        f.write(json.dumps(item) + "\n")

print(f"✅ Saved {len(manifest_entries)} agenda chunks to {DEST}")