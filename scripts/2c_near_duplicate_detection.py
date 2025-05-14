

import os
import json
from pathlib import Path
from tqdm import tqdm
import pdfplumber
from datasketch import MinHash, MinHashLSH

# CONFIG
DOC_REGISTER_PATH = Path("data/processed_register/document_ids.json")
MANIFEST_PATH = Path("data/processed_register/document_manifest.jsonl")
COUNCIL_DOCS_PATH = Path("data/council_documents/")
SHINGLE_SIZE = 5
MINHASH_PERMUTATIONS = 128
SIMILARITY_THRESHOLD = 0.95

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
    except Exception:
        return ""

def get_shingles(text, size):
    words = text.lower().split()
    return set([" ".join(words[i:i+size]) for i in range(len(words) - size + 1)])

def build_minhash(shingles):
    m = MinHash(num_perm=MINHASH_PERMUTATIONS)
    for s in shingles:
        m.update(s.encode('utf-8'))
    return m

def main():
    print("Loading document manifest...")
    manifest = load_manifest()
    path_to_entry = {}
    docid_to_text = {}
    docid_to_minhash = {}

    for entry in tqdm(manifest, desc="Extracting and hashing text"):
        rel_path = entry.get("path") or entry.get("file_path")
        doc_id = entry.get("doc_id")
        if not rel_path or not doc_id:
            continue
        file_path = COUNCIL_DOCS_PATH / rel_path
        if not file_path.exists():
            continue
        text = extract_text(file_path)
        shingles = get_shingles(text, SHINGLE_SIZE)
        if not shingles:
            continue
        mh = build_minhash(shingles)
        docid_to_text[doc_id] = text
        docid_to_minhash[doc_id] = mh
        path_to_entry[doc_id] = entry

    print("Building LSH index...")
    lsh = MinHashLSH(threshold=SIMILARITY_THRESHOLD, num_perm=MINHASH_PERMUTATIONS)
    for doc_id, mh in docid_to_minhash.items():
        lsh.insert(doc_id, mh)

    print("Checking for near-duplicates...")
    updated_manifest = []
    for doc_id, mh in tqdm(docid_to_minhash.items(), desc="Querying LSH"):
        similar_ids = lsh.query(mh)
        similar_ids = [sid for sid in similar_ids if sid != doc_id]
        if similar_ids:
            primary = min(similar_ids + [doc_id])
            if doc_id != primary:
                entry = path_to_entry[doc_id]
                entry["is_near_duplicate_of"] = primary
        updated_manifest.append(path_to_entry[doc_id])

    print(f"Near-duplicates flagged: {len([e for e in updated_manifest if 'is_near_duplicate_of' in e])}")
    save_manifest(updated_manifest)
    print("Manifest updated.")

if __name__ == "__main__":
    main()