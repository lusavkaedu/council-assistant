# pdf_processor/4_summarise_AI_pdfs.py
# This script generates a summary of committees from KCC meeting data.


import os
import json
import random
import time
from datetime import datetime
from pathlib import Path
import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF
import openai
import requests
from tqdm import tqdm
import hashlib

# Imports from 2_classify_pdfs.py
import sys
import os

# Dynamically add the project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))  # one level up
sys.path.append(project_root)

from pdf_processor.utils.classify_pdfs import get_document_category

# === CONFIGURATION ===
EXCLUDED_CATEGORIES = {"eqia", "glossary"}
METADATA_PATH = Path("data/metadata/documents_test.jsonl")
PDF_CACHE_DIR = Path("data/tmp_pdfs/")
PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
FULL_TEXT_DIR = Path("data/pdf_full_text/")
FULL_TEXT_DIR.mkdir(parents=True, exist_ok=True)
#OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_MODEL = "gpt-4o-mini"
MAX_WORDS = 800
WORK_HOURS = range(7, 22)  # 8am to 6pm
THROTTLE_SECONDS = (1, 5)  # Mimic human delays between requests


# === INITIAL SETUP ===
client = OpenAI(api_key=st.secrets["openai_api_key"])
def download_pdf(url, doc_id):
    response = requests.get(url)
    if response.status_code == 200:
        pdf_path = PDF_CACHE_DIR / f"{doc_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        return pdf_path
    else:
        raise Exception(f"Failed to download PDF: {url}")

def is_work_hour():
    now = datetime.now()
    return now.hour in WORK_HOURS and now.weekday() < 5  # Mon–Fri

def extract_pdf_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        full_text = []
        for page in doc:
            full_text.append(page.get_text())
        doc.close()
        return ' '.join(full_text)
    except Exception as e:
        return f"ERROR: {e}"

def extract_pdf_metadata(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        doc.close()
        return {k: v for k, v in metadata.items() if v}  # remove empty values
    except Exception as e:
        return {"error": f"Metadata extraction failed: {e}"}

def count_tables(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        num_tables = 0
        for page in doc:
            tables = page.find_tables()
            if tables:
                num_tables += len(tables.tables)
        doc.close()
        return num_tables
    except Exception as e:
        return -1  # fallback value on error

def short_hash(value: str, length=6):
    return hashlib.sha1(value.encode()).hexdigest()[:length]


# def classify_document(filename, snippet):
#     name = filename.lower()
#     if "agenda" in name:
#         return "agenda"
#     elif "minutes" in name:
#         return "minutes"
#     elif "budget" in name:
#         return "budget"
#     elif "report" in name:
#         return "report"
#     elif "motion" in name:
#         return "motion"
#     else:
#         if "resolved" in snippet.lower() or "approved" in snippet.lower():
#             return "decision"
#         return "other"

def ask_gpt_summary_and_keywords(snippet, source_filename="", metadata_title="", committee=None, meeting_date=None):
    prompt = f'''
You are an AI assistant helping to classify and summarize council documents.

Based on the inputs below, return your output in valid JSON format using the following structure:

{{
  "display_title": "<A concise, human-readable title for the document suitable for display in a UI>",
  "summary": "<A 2-sentence description of what the document is about>",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

Only return a valid JSON object—no extra text or commentary.

filename: "{source_filename}"
metadata_title: "{metadata_title}"
'''
    if committee:
        prompt += f"\ncommittee: \"{committee}\""
    if meeting_date:
        prompt += f"\nmeeting_date: \"{meeting_date}\""

    prompt += f"\n\nExtract:\n{snippet}\n"

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return {"display_title": "", "summary": f"ERROR: {e}", "keywords": []}

lines = list(open(METADATA_PATH, "r", encoding="utf-8"))

with open(METADATA_PATH, "w", encoding="utf-8") as f_out:
    for line in tqdm(lines, desc="Processing documents"):
        doc = json.loads(line)
        if doc.get("doc_category", "").lower() in EXCLUDED_CATEGORIES or doc.get("status") != "pending":
            f_out.write(json.dumps(doc, ensure_ascii=False).rstrip() + "\n")
            continue
        try:
            print(f"🔍 Downloading: {doc['url']}")
            source_filename = os.path.basename(doc["url"])
            doc_id = doc.get("doc_id", os.path.basename(doc["url"]))
            pdf_path = download_pdf(doc["url"], doc_id)
            full_text = extract_pdf_text(pdf_path)
            num_tables = count_tables(pdf_path)
            pdf_metadata = extract_pdf_metadata(pdf_path)
            words = full_text.strip().split()
            snippet = ' '.join(words[:min(MAX_WORDS, len(words))])
            category = get_document_category(doc.get("url", ""))

            metadata_title = pdf_metadata.get("title", "")

            gpt_response = ask_gpt_summary_and_keywords(
                snippet,
                source_filename=source_filename,
                metadata_title=metadata_title,
                committee=doc.get("committee_name", ""),
                meeting_date=str(doc.get("meeting_date", ""))
            )
            full_text_path = FULL_TEXT_DIR / f"{doc_id}.txt"
            with open(full_text_path, "w", encoding="utf-8") as f_text:
                f_text.write(full_text)

            doc.update({
                "summary": gpt_response.get("summary", ""),
                "keywords": gpt_response.get("keywords", []),
                "full_text_path": str(full_text_path),
                "num_tables_detected": num_tables,
                "pdf_metadata": pdf_metadata,
                "status": "complete",
                "timestamp": datetime.now().isoformat(),
                "source_filename": source_filename,
                "metadata_title": metadata_title,
                "display_title": gpt_response.get("display_title", ""),
            })
            print(f"[✔] Processed: {doc_id}")
            delay = random.randint(*THROTTLE_SECONDS)
            print(f"🕒 Sleeping for {delay}s...")
            time.sleep(delay)

            if pdf_path.exists():
                pdf_path.unlink()
        except Exception as e:
            doc["status"] = "error"
            doc["error_msg"] = str(e)
            print(f"❌ Error: {doc_id} — {e}")
        f_out.write(json.dumps(doc, ensure_ascii=False).rstrip() + "\n")
print("🎉 All PDFs processed.")
