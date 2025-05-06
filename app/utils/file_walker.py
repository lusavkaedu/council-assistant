# app/utils/file_walker.py
"""
Recursively walks the council_documents directory to find PDF files.
Skips already-processed files unless 'force' is specified.
"""
import os

def find_all_chunks(root_dir="data/council_documents"):
    import os
    chunk_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith("_chunks.json"):
                chunk_files.append(os.path.join(dirpath, file))
    return chunk_files

def find_all_pdfs(root_dir, extension=".pdf"):
    pdf_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(extension):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

# scripts/process_all.py
"""
Entry point to batch process all PDFs in council_documents into processed_chunks.
"""
import os
import json
from app.utils.file_walker import find_all_pdfs
from app.utils.processor import process_pdf

RAW_DIR = "data/council_documents"
OUTPUT_DIR = "data/processed_chunks"

# Dummy routing by keyword in path (to be replaced with proper mapping)
def infer_committee(path):
    return path.split("/")[-2]

def infer_doc_type(filename):
    name = filename.lower()
    if "agenda" in name:
        return "agenda"
    elif "minutes" in name:
        return "minutes"
    else:
        return "report"


def main():
    pdfs = find_all_pdfs(RAW_DIR)
    for path in pdfs:
        committee = infer_committee(path)
        doc_type = infer_doc_type(path)
        chunks = process_pdf(path, committee, doc_type)

        # Determine save path
        rel = path.replace(RAW_DIR, "").strip("/")
        folder = os.path.join(OUTPUT_DIR, os.path.dirname(rel))
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(folder, f"{base}_chunks.json")

        os.makedirs(folder, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        print(f"✅ Processed {len(chunks)} chunks from {path}")

if __name__ == "__main__":
    main()
