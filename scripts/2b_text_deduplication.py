

import os
import json
import hashlib
from pathlib import Path
from tqdm import tqdm
import pdfplumber

# CONFIG
DOC_REGISTER_PATH = Path("data/processed_register/document_ids.json")
MANIFEST_PATH = Path("data/processed_register/document_manifest.jsonl")
COUNCIL_DOCS_PATH = Path("data/council_documents/")
TEXT_HASH_KEY = "text_hash"
DUPLICATE_KEY = "is_text_duplicate_of"

def load_register():
    with open(DOC_REGISTER_PATH, "r") as f:
        return json.load(f)

def load_manifest():
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH, "r") as f:
        return [json.loads(line) for line in f]

def save_manifest(entries):
    with open(MANIFEST_PATH, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

def extract_text(filepath):
    try:
        with pdfplumber.open(filepath) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        return ""

def compute_text_hash(text):
    cleaned = " ".join(text.split()).lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

def main():
    print("Loading register and manifest...")
    doc_register = load_register()
    manifest = load_manifest()
    path_to_docid = {v["path"]: k for k, v in doc_register.items()}
    seen_hashes = {}
    updated_manifest = []

    print("Scanning documents for textual duplicates...")
    for entry in tqdm(manifest):
        rel_path = entry.get("path") or entry.get("file_path")
        if not rel_path:
            updated_manifest.append(entry)
            continue

        file_path = COUNCIL_DOCS_PATH / rel_path
        if not file_path.exists():
            updated_manifest.append(entry)
            continue

        text = extract_text(file_path)
        text_hash = compute_text_hash(text)
        entry[TEXT_HASH_KEY] = text_hash

        if text_hash in seen_hashes:
            entry[DUPLICATE_KEY] = seen_hashes[text_hash]
        else:
            seen_hashes[text_hash] = entry.get("doc_id")

        updated_manifest.append(entry)

    print(f"Found {len([e for e in updated_manifest if DUPLICATE_KEY in e])} text duplicates.")
    save_manifest(updated_manifest)
    print("Manifest updated.")

if __name__ == "__main__":
    main()