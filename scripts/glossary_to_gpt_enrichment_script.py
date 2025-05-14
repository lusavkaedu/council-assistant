
import os
import re
import json
import time
import openai
from PyPDF2 import PdfReader
from tqdm import tqdm

# === CONFIGURATION ===
PDF_PATH = "glossary.pdf"  # Rename to your file
OUTPUT_JSONL = "enriched_glossary.jsonl"
OPENAI_MODEL = "gpt-4"
API_KEY = os.getenv("OPENAI_API_KEY")  # Or set directly here
DELAY_BETWEEN_CALLS = 2  # seconds between requests to avoid throttling

# === SETUP ===
openai.api_key = API_KEY

# === STEP 1: Extract glossary-style entries from PDF ===
def extract_terms_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    entries = []
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        next_line = lines[i + 1]
        if re.match(r'^[A-Z0-9 \-/]+$', line) and not next_line.isupper():
            term = line.strip()
            definition_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^[A-Z0-9 \-/]+$', lines[i]):
                definition_lines.append(lines[i])
                i += 1
            definition = " ".join(definition_lines).strip()
            entries.append({"term": term, "definition": definition})
        else:
            i += 1
    return entries

# === STEP 2: Clean definitions ===
def clean_text(text):
    text = re.sub(r'\b([a-zA-Z])\s+([a-zA-Z])\b', r'\1\2', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\bMana gement\b', 'Management', text)
    text = re.sub(r'\bRe quiremen t\b', 'Requirement', text)
    text = re.sub(r'\bCapi ta l\b', 'Capital', text)
    return text.strip()

# === STEP 3: Send to GPT ===
def enrich_with_gpt(entry):
    prompt = f"""You are a glossary enrichment expert. Given the following term and its definition,
return a JSON object with the following fields:
- explanation_for_chat
- tooltip_short (max 10 words)
- tags (2–5 words)
- related_terms (2–4 terms)

Term: {entry['term']}
Definition: {entry['definition']}"""

    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        gpt_data = json.loads(response["choices"][0]["message"]["content"])
        enriched = {**entry, **gpt_data}
        return enriched
    except Exception as e:
        print(f"Error enriching {entry['term']}: {e}")
        return None

# === STEP 4: Main Process ===
def process_pdf_and_enrich(pdf_path, output_path):
    entries = extract_terms_from_pdf(pdf_path)
    print(f"Found {len(entries)} terms to process...")

    with open(output_path, "a", encoding="utf-8") as f:
        for entry in tqdm(entries):
            entry["definition"] = clean_text(entry["definition"])
            enriched = enrich_with_gpt(entry)
            if enriched:
                f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                time.sleep(DELAY_BETWEEN_CALLS)

# === RUN ===
# Uncomment the following line when running locally:
# process_pdf_and_enrich(PDF_PATH, OUTPUT_JSONL)
