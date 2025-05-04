import os
import re
import pdfplumber
from pathlib import Path

ROOT_DIR = "data/council_documents"
SCAN_TARGETS = ["committees", "cabinet", "full_council"]

# Month mapping
month_map = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

# Regex patterns
pattern_full = re.compile(r"(\d{1,2})[\s\-]*(January|February|March|April|May|June|July|August|September|October|November|December)[\s\-]*(\d{4})", re.IGNORECASE)
pattern_numeric = re.compile(r"\b(0[1-9]|[12]\d|3[01])[\/\-\.](0[1-9]|1[0-2])[\/\-\.](20\d{2})\b")

def extract_date_from_text(text):
    match = pattern_full.search(text)
    if match:
        day, month_name, year = match.groups()
        month = month_map[month_name.lower()]
        return f"{year}-{month}-{day.zfill(2)}"
    
    match = pattern_numeric.search(text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    
    return None

def scan_pdfs():
    for target in SCAN_TARGETS:
        base_path = os.path.join(ROOT_DIR, target)
        for dirpath, _, filenames in os.walk(base_path):
            if any(x in dirpath for x in ["originals", "text_chunks", "tables"]):
                continue
            for file in filenames:
                if not file.lower().endswith(".pdf"):
                    continue
                full_path = os.path.join(dirpath, file)

                try:
                    with pdfplumber.open(full_path) as pdf:
                        text = pdf.pages[0].extract_text() or ""
                        date = extract_date_from_text(text)
                        if date:
                            print(f"✅ {date}  ←  {file}")
                        else:
                            print(f"⚠️  No date found: {file}")
                except Exception as e:
                    print(f"❌ Error reading {file}: {e}")

if __name__ == "__main__":
    scan_pdfs()
