import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader
import nltk

# Download NLTK data if not already present
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

# === CONFIGURATION ===
base_dir = Path("data/council_documents")
register_path = Path("data/processed_register/document_ids.json")
chunk_suffix = "_chunks.json"
skip_existing = True
max_workers = 4  # Parallelism

# === Load register ===
with open(register_path) as f:
    doc_register = json.load(f)

# === Collect PDFs to process ===
def collect_pdf_paths():
    pdfs = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue
            full_path = Path(root) / file
            if "originals" not in full_path.parts:
                continue
            rel_path = str(full_path.relative_to(base_dir))
            if rel_path not in doc_register:
                print(f"⚠️ Skipped unregistered: {rel_path}")
                continue
            chunk_path = full_path.with_name(full_path.stem + chunk_suffix)
            if skip_existing and chunk_path.exists():
                continue
            pdfs.append(full_path)
    return pdfs

# === Chunk a single PDF ===
def process_pdf(pdf_path):
    try:
        rel_path = str(pdf_path.relative_to(base_dir))
        doc_id = doc_register[rel_path]

        # Parse committee and meeting date from path
        parts = pdf_path.parts
        committee = parts[-4]
        meeting_date = parts[-3]

        # Load and chunk
        reader = PDFReader()
        docs = reader.load_data(file=pdf_path)
        splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)
        nodes = splitter.get_nodes_from_documents(docs)

        # Format chunks
        chunks = []
        for i, node in enumerate(nodes):
            chunks.append({
                "chunk_id": f"{doc_id}_chunk_{i:03}",
                "document_id": doc_id,
                "text": node.text,
                "committee": committee,
                "meeting_date": meeting_date,
                "original_filename": pdf_path.name,
                "chunk_index": i,
                "chunk_char_start": node.start_char_idx,
                "chunk_char_end": node.end_char_idx
            })

        # Save output
        output_path = pdf_path.with_name(pdf_path.stem + chunk_suffix)
        with open(output_path, "w") as f:
            json.dump(chunks, f, indent=2)

        print(f"✅ Chunked: {rel_path} ({len(chunks)} chunks)")
    except Exception as e:
        print(f"❌ Failed: {pdf_path} — {e}")

# === Run ===
if __name__ == "__main__":
    all_pdfs = collect_pdf_paths()
    print(f"🔍 Found {len(all_pdfs)} PDFs to process...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_pdf, all_pdfs)

    print("📊 Done.")