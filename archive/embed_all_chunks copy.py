"""
Main chunking script:
- Loads all PDFs under data/council_documents/
- Extracts text, cleans, splits semantically with overlap
- Adds metadata including doc_id, committee, meeting_date
- Saves to data/processed_chunks/<committee>/<meeting_date>/<filename>_chunks.json
"""

import os
import json
from pathlib import Path
from tqdm import tqdm
from hashlib import md5

from app.utils.text_extractor import extract_text_from_pdf
from app.utils.processor import clean_text, split_into_chunks_semantically  # assumes semantic chunker
from app.utils.date_extractor import extract_date_from_filename  # or from content

PDF_DIR = Path("data/council_documents")
CHUNK_DIR = Path("data/processed_chunks")
REGISTER_PATH = Path("data/processed_register/document_ids.json")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Load document ID register
with open(REGISTER_PATH) as f:
    doc_id_lookup = json.load(f)

# Process each PDF
for pdf_path in tqdm(list(PDF_DIR.rglob("*.pdf")), desc="Processing PDFs"):
    try:
        rel_path = pdf_path.relative_to(PDF_DIR)
        rel_str = str(rel_path)
        committee = rel_path.parts[0]
        meeting_date = rel_path.parts[1]
        filename = pdf_path.stem

        doc_id_entry = doc_id_lookup.get(rel_str)
        if not doc_id_entry:
            print(f"⚠️ Skipping {rel_str} — no doc_id assigned.")
            continue
        doc_id = doc_id_entry["id"]

        # Extract + clean
        pages = extract_text_from_pdf(pdf_path)
        all_chunks = []
        for page_num, text in pages:
            cleaned = clean_text(text)
            chunks = split_into_chunks_semantically(cleaned, CHUNK_SIZE, CHUNK_OVERLAP)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "text": chunk,
                    "doc_id": doc_id,
                    "committee": committee,
                    "meeting_date": meeting_date,
                    "page_num": page_num,
                    "chunk_id": i,
                    "source_file": str(rel_path)
                })

        # Save
        out_dir = CHUNK_DIR / committee / meeting_date
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{filename}_chunks.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        print(f"✅ {filename}: {len(all_chunks)} chunks")

    except Exception as e:
        print(f"❌ Failed {pdf_path}: {e}")
