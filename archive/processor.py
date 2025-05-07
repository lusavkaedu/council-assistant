# ✅ Final `processor.py`
# Consolidated with chunker.py and clean use of date_extractor and text_extractor

import os
import json
from pathlib import Path
from app.utils.text_extractor import extract_text_from_pdf
from app.utils.date_extractor import extract_date_from_filename
import re

CHUNK_SIZE = 500


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # Single newlines → space
    text = re.sub(r"\s{2,}", " ", text)             # Multiple spaces → single
    text = re.sub(r"\n{2,}", "\n", text)           # Multiple newlines → single
    text = re.sub(r"\bPage\s*\d+\b", "", text, flags=re.IGNORECASE)
    return text.strip()


def split_into_chunks(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]


def process_pdf(pdf_path: str, chunk_size=CHUNK_SIZE):
    full_path = Path(pdf_path)
    date = extract_date_from_filename(full_path.name)

    try:
        pages = extract_text_from_pdf(full_path)
    except Exception as e:
        print(f"❌ Failed to read {pdf_path}: {e}")
        return

    chunks = []
    for i, (page_number, text) in enumerate(pages):
        cleaned = clean_text(text)
        subchunks = split_into_chunks(cleaned, chunk_size)
        for j, chunk in enumerate(subchunks):
            chunks.append({
                "source": full_path.name,
                "page": page_number,
                "chunk_id": j,
                "date": date,
                "content": chunk
            })

    # Determine save path
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(os.path.dirname(pdf_path), f"{base}_chunks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"✅ Processed {len(chunks)} chunks from {pdf_path}")
