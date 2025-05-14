"""
1_chunking_master.py

Standalone script to clean and semantically chunk all council PDFs.
Avoids external dependencies like llama-index. Uses regex-based sentence chunking.
"""

import os
import re
import json
from pathlib import Path
from hashlib import md5
from tqdm import tqdm
import warnings
warnings.filterwarnings("ignore")

# Parallel processing
from concurrent.futures import ThreadPoolExecutor, as_completed

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# CONFIG
PDF_DIR = Path("data/council_documents")
CHUNK_DIR = Path("data/processed_chunks")
REGISTER_PATH = Path("data/processed_register/document_ids.json")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def split_into_chunks_semantically(text, chunk_size=500, overlap=50):
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    chunks = []
    current_chunk = []
    current_start = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if sum(len(s) for s in current_chunk) + sentence_len <= chunk_size:
            current_chunk.append(sentence)
        else:
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "char_start": current_start,
                    "char_end": current_start + len(chunk_text)
                })
                current_start += len(chunk_text) + 1  # add 1 for space/newline between chunks
            current_chunk = current_chunk[-(overlap // 100):] if overlap else []
            current_chunk.append(sentence)

    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "text": chunk_text,
            "char_start": current_start,
            "char_end": current_start + len(chunk_text)
        })

    return chunks

def extract_text_from_pdf(pdf_path):
    import pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return [(i+1, page.extract_text() or "") for i, page in enumerate(pdf.pages)]
    except Exception as e:
        tqdm.write(f"❌ Could not read {pdf_path}: {e}")
        return []

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

# Load document IDs
with open(REGISTER_PATH) as f:
    doc_id_lookup = json.load(f)


# Collect all PDF paths
def collect_pdf_paths():
    return list(PDF_DIR.rglob("*.pdf"))

# Process a single PDF (refactored from above loop)
def process_pdf(pdf_path):
    rel_path = pdf_path.relative_to(PDF_DIR)
    rel_str = str(rel_path)
    parts = rel_path.parts

    if "originals" not in parts:
        tqdm.write(f"⚠️ Skipping {rel_str} (missing 'originals')")
        return

    try:
        originals_index = parts.index("originals")
        committee = parts[originals_index - 2] if parts[0] == "committees" else parts[0]
        meeting_date = parts[originals_index - 1]
    except IndexError:
        tqdm.write(f"⚠️ Skipping {rel_str} (unable to parse committee/date)")
        return
    filename = pdf_path.stem

    out_dir = CHUNK_DIR / committee / meeting_date
    out_file = out_dir / f"{filename}_chunks.json"
    if out_file.exists():
        tqdm.write(f"⏭️  Skipping {rel_str} — already chunked")
        return

    doc_id_entry = doc_id_lookup.get(rel_str)
    if not doc_id_entry:
        tqdm.write(f"⚠️ Skipping {rel_str} — no doc_id assigned.")
        return
    doc_id = doc_id_entry["id"]

    # Extract, clean, chunk
    pages = extract_text_from_pdf(pdf_path)
    all_chunks = []
    for page_num, raw_text in pages:
        cleaned = clean_text(raw_text)
        chunks = split_into_chunks_semantically(cleaned, CHUNK_SIZE, CHUNK_OVERLAP)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "text": chunk["text"],
                "doc_id": doc_id,
                "committee": committee,
                "meeting_date": meeting_date,
                "page_num": page_num,
                "chunk_id": i,
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
                "source_file": rel_str
            })

    # Save
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    tqdm.write(f"✅ {rel_str}: {len(all_chunks)} chunks")

# Process all PDFs in parallel using ThreadPoolExecutor
def process_all_pdfs_parallel(all_pdfs):
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_pdf = {executor.submit(process_pdf, pdf): pdf for pdf in all_pdfs}
        for future in as_completed(future_to_pdf):
            try:
                future.result()
            except Exception as e:
                tqdm.write(f"❌ Error processing {future_to_pdf[future]}: {e}")

# Run parallel processing
if __name__ == "__main__":
    all_pdfs = collect_pdf_paths()
    tqdm.write(f"🔍 Found {len(all_pdfs)} PDFs to process...")

    process_all_pdfs_parallel(all_pdfs)

    tqdm.write("📊 Done.")