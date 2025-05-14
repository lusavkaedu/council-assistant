# ✅ Final `text_extractor.py`
# Handles PDF text extraction using pdfplumber, with basic fallback warnings

import pdfplumber

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from each page of a PDF.
    Returns a list of (page_number, text) tuples.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
            except Exception as e:
                text = f"[Error extracting page {i+1}: {e}]"
            pages.append((i + 1, text))
    return pages
