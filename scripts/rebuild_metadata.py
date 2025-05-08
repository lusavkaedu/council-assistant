import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path("data/council_documents")
OUTPUT_PATH = Path("data/merged_metadata.pkl")
RESULTS = []

# Scan for PDF files in the nested structure: <committee>/<meeting_date>/originals/*.pdf
pdf_files = list(BASE_DIR.rglob("originals/*.pdf"))
print(f"🔍 Found {len(pdf_files)} PDF files")

# Group PDFs by their originals folder to write metadata.json per folder
folders = {}
for pdf_path in pdf_files:
    # Extract committee and meeting_date from folder structure
    try:
        # pdf_path example: data/council_documents/<committee>/<meeting_date>/originals/file.pdf
        meeting_date = pdf_path.parent.parent.name
        committee = pdf_path.parent.parent.parent.name
    except Exception:
        continue

    rel_path = pdf_path.relative_to(BASE_DIR)
    metadata_entry = {
        "committee": committee,
        "meeting_date": meeting_date,
        "filename": pdf_path.name,
        "source_path": str(rel_path)
    }

    folder_key = pdf_path.parent
    if folder_key not in folders:
        folders[folder_key] = []
    folders[folder_key].append(metadata_entry)

# Write metadata.json files in each originals folder
for folder_path, metadata_list in folders.items():
    metadata_path = folder_path / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2)

chunk_files = list(BASE_DIR.rglob("chunks/*.json"))
print(f"🔍 Found {len(chunk_files)} chunk files")

for chunk_path in tqdm(chunk_files):
    try:
        with chunk_path.open("r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Locate metadata.json from parent of parent (e.g., meeting folder / originals)
        metadata_path = chunk_path.parent.parent / "metadata.json"
        url_lookup = {}
        if metadata_path.exists():
            try:
                with metadata_path.open("r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                    for item in meta:
                        item["filename"] = Path(item["filename"]).name
                    url_lookup = {
                        item["filename"]: {
                            "committee": item.get("committee", ""),
                            "meeting_date": item.get("meeting_date", ""),
                            "source_path": item.get("source_path", "")
                        } for item in meta
                    }
            except Exception as e:
                print(f"Warning: Couldn't load {metadata_path} → {e}")

        for chunk in chunks:
            filename = chunk.get("filename", "")
            url_info = url_lookup.get(filename, {})
            record = {
                "doc_id": chunk.get("doc_id"),
                "chunk_id": chunk.get("chunk_id"),
                "text": chunk.get("text"),
                "committee": url_info.get("committee", chunk.get("committee")),
                "meeting_date": url_info.get("meeting_date", chunk.get("meeting_date")),
                "page_num": chunk.get("page_num"),
                "filename": filename,
                "source_file": chunk.get("source_file"),
                "source": chunk.get("source"),
                "source_path": url_info.get("source_path", ""),
                "source_exists": (BASE_DIR / Path(chunk.get("source", ""))).exists()
            }
            RESULTS.append(record)

    except Exception as e:
        print(f"⚠️ Skipping file due to error: {chunk_path} — {e}")

# Save as DataFrame
df = pd.DataFrame(RESULTS)
df = df[df["source_exists"]]
df.drop(columns=["source_exists"], inplace=True)
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_pickle(OUTPUT_PATH)
print(f"✅ Saved {len(df)} rows to {OUTPUT_PATH}")