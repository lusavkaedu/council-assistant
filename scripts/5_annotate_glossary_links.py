import json
from pathlib import Path
import re
from collections import defaultdict

# --- Config ---
GLOSSARY_PATH = Path("data/glossary/glossary.json")
CHUNKS_ROOT = Path("data/council_documents")
METADATA_PATH = Path("data/document_metadata/raw_scraped_metadata.jsonl")
DRY_RUN = False

# --- Load glossary ---
with GLOSSARY_PATH.open("r", encoding="utf-8") as f:
    glossary = json.load(f)

term_map = {}
for entry in glossary:
    canonical = entry["term"]
    term_map[canonical.lower()] = canonical
    for alias in entry.get("aliases", []):
        term_map[alias.lower()] = canonical

# --- Scan and annotate chunks ---
chunk_files = list(CHUNKS_ROOT.rglob("*_chunks.json"))
doc_to_terms = defaultdict(set)

def find_glossary_terms(text):
    text_lower = text.lower()
    found = set()
    for alias_lower, canonical in term_map.items():
        if re.search(rf"\b{re.escape(alias_lower)}\b", text_lower):
            found.add(canonical)
    return list(found)

for chunk_file in chunk_files:
    with chunk_file.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    for chunk in chunks:
        terms = find_glossary_terms(chunk.get("text", ""))
        chunk["glossary_terms"] = terms
        doc_to_terms[chunk["doc_id"]].update(terms)

    if DRY_RUN:
        print(f"\nDRY RUN — {chunk_file.name} sample annotations:")
        for c in chunks[:3]:
            print({"chunk_id": c.get("chunk_id"), "glossary_terms": c.get("glossary_terms")})
    else:
        with chunk_file.open("w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

# --- Update metadata warehouse ---
new_metadata_lines = []
with METADATA_PATH.open("r", encoding="utf-8") as f:
    for line in f:
        record = json.loads(line)
        record["glossary_terms"] = sorted(doc_to_terms.get(record.get("doc_id", ""), []))
        new_metadata_lines.append(json.dumps(record))

if DRY_RUN:
    print("\nDRY RUN — Updated metadata records:")
    for line in new_metadata_lines[:3]:
        r = json.loads(line)
        print({"doc_id": r.get("doc_id"), "glossary_terms": r.get("glossary_terms")})
else:
    with METADATA_PATH.open("w", encoding="utf-8") as f:
        for line in new_metadata_lines:
            f.write(line + "\n")
