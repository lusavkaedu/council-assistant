"""
Entry point to batch process all PDFs in council_documents into processed_chunks.
"""

import os
import json
from app.utils.file_walker import find_all_pdfs
from app.utils.processor import process_pdf

RAW_DIR = "data/council_documents"

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
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(os.path.dirname(path), f"{base}_chunks.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)


        print(f"✅ Processed {len(chunks)} chunks from {path}")

if __name__ == "__main__":
    main()
