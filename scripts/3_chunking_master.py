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
import pdfplumber
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import warnings

# Configurations
PDF_DIR = Path("data/council_documents")
# CHUNK_DIR = Path("data/processed_chunks")
REGISTER_PATH = Path("data/processed_register/document_ids.json")
CHUNK_SIZE = 500  # Adjust as needed
CHUNK_OVERLAP = 50  # Percentage overlap between chunks

# Logging and warnings setup
logging.getLogger("pdfminer").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


# Function to clean text: Remove headers, footers, and boilerplate content
def clean_text(text):
    # Remove headers/footers and unwanted boilerplate content
    if not text:
        return ""
    
    # Remove lines with common header/footer patterns (customize for your needs)
    text = re.sub(r'(?i)(agenda|minutes|kent county council|date|subject|confidential|private)', '', text)
    
    # Replace unwanted newlines and excessive spaces
    text = re.sub(r"(?<!\\n)\\n(?!\\n)", " ", text)  # Single newlines → space
    text = re.sub(r"\s{2,}", " ", text)             # Multi spaces → single space

    return text.strip()


# Split the text into chunks based on sentence boundaries, keeping overlap and semantic boundaries
def split_into_chunks_semantically(text, chunk_size=500, overlap=50):
    sentences = re.split(r'(?<=[.!?]) +', text.strip())  # Split by punctuation
    chunks = []
    current_chunk = []
    current_start = 0  # To track the start position of each chunk
    char_count = 0  # To track the character length of the chunk

    for sentence in sentences:
        sentence_len = len(sentence)

        # Check if adding this sentence would exceed the chunk size
        if char_count + sentence_len <= chunk_size:
            current_chunk.append(sentence)
            char_count += sentence_len + 1  # Include space/newline between sentences
        else:
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "char_start": current_start,
                    "char_end": current_start + len(chunk_text),
                })
                current_start += len(chunk_text) + 1  # Add space/newline
            # Ensure overlap between chunks
            if overlap:
                overlap_size = int(overlap * chunk_size / 100)
                # Calculate how many sentences to keep for overlap
                overlap_sentences = []
                overlap_len = 0
                for sent in reversed(current_chunk):
                    overlap_len += len(sent) + 1
                    overlap_sentences.insert(0, sent)
                    if overlap_len >= overlap_size:
                        break
                current_chunk = overlap_sentences
            else:
                current_chunk = []
            current_chunk.append(sentence)
            char_count = len(sentence) + 1  # Start a new chunk, reset character count

    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "text": chunk_text,
            "char_start": current_start,
            "char_end": current_start + len(chunk_text),
        })

    return chunks


# Extract text from a PDF file using pdfplumber
def extract_text_from_pdf(pdf_path):
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append((i + 1, text))  # (page_num, page_text)
    except Exception as e:
        tqdm.write(f"❌ Could not read {pdf_path}: {e}")
    return pages


# Process each PDF document
def process_pdf(pdf_path):
    rel_path = pdf_path.relative_to(PDF_DIR)
    rel_str = str(rel_path)
    parts = rel_path.parts

    if "originals" not in parts:
        tqdm.write(f"⚠️ Skipping {rel_str} (missing 'originals')")
        return

    try:
        originals_index = parts.index("originals")
        committee = parts[originals_index - 2]
        meeting_date = parts[originals_index - 1]
    except IndexError:
        tqdm.write(f"⚠️ Skipping {rel_str} (unable to parse committee/date)")
        return
    filename = pdf_path.stem

    out_dir = pdf_path.parent.parent / "chunks"
    out_file = out_dir / f"{filename}_chunks.json"
    if out_file.exists():
        try:
            out_file.unlink()
            tqdm.write(f"🗑️  Deleted previous chunk for {rel_str}")
        except Exception as e:
            tqdm.write(f"❌ Failed to delete existing chunk for {rel_str}: {e}")

    # Retrieve document ID from register
    doc_id_entry = doc_id_lookup.get(rel_str)
    if not doc_id_entry:
        tqdm.write(f"⚠️ Skipping {rel_str} — no doc_id assigned.")
        return
    doc_id = doc_id_entry["id"]

    # Extract, clean, chunk
    pages = extract_text_from_pdf(pdf_path)
    all_chunks = []
    for page_num, raw_text in pages:
        cleaned = clean_text(raw_text)  # Clean extracted text
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

    # Save to a temporary file first, then rename to avoid partial writes
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = out_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    tmp_file.rename(out_file)

    manifest_updates.append({
        "relative_path": rel_str,
        "chunk_path": str(out_file),
        "status": "ready_for_embedding"
    })

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


# Main function to run the chunking process
if __name__ == "__main__":
    # Load document IDs
    with open(REGISTER_PATH) as f:
        doc_id_lookup = json.load(f)

    manifest_updates = []

    all_pdfs = list(PDF_DIR.rglob("*.pdf"))
    tqdm.write(f"🔍 Found {len(all_pdfs)} PDFs to process...")

    process_all_pdfs_parallel(all_pdfs)

    # Apply manifest updates (thread-safe, after all threads complete)
    manifest_path = Path("data/processed_register/document_manifest.jsonl")
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            existing_lines = [json.loads(line) for line in f if line.strip()]

        # Apply updates
        for update in manifest_updates:
            for entry in existing_lines:
                if entry.get("relative_path") == update["relative_path"]:
                    entry["chunk_path"] = update["chunk_path"]
                    entry["status"] = update["status"]

        with open(manifest_path, "w", encoding="utf-8") as f:
            for entry in existing_lines:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        tqdm.write(f"📦 Manifest updated with {len(manifest_updates)} chunked files.")

    tqdm.write("📊 Done.")