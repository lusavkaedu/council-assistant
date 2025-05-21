# pdf_processor/claude_summarization_script.py
# This script generates summaries of PDFs using OpenAI.

import os
import json
import time
from datetime import datetime
from pathlib import Path
import streamlit as st
from openai import OpenAI
import sys
from tqdm import tqdm

# Dynamically add the project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))  # one level up
sys.path.append(project_root)

from pdf_processor.utils.classify_pdfs import get_document_category

# === CONFIGURATION ===
EXCLUDED_CATEGORIES = {"eqia", "glossary"}
METADATA_PATH = Path("data/metadata/documents.jsonl")
MANIFEST_PATH = Path("data/processed_register/pdf_manifest_test.jsonl")
MANIFEST_BACKUP_PATH = Path("data/processed_register/pdf_manifest_backup.jsonl")
PDF_METADATA_DIR = Path("data/pdf_metadata/")
SUMMARY_DIR = Path("data/pdf_summaries/")
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
OPENAI_MODEL = "gpt-4o-mini"  # Change as needed
MAX_WORDS = 800
THROTTLE_SECONDS = 3  # Delay between API calls

# === INITIAL SETUP ===
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    project=os.environ.get("OPENAI_PROJECT_ID")
)

def load_manifest():
    """Load the document processing manifest."""
    manifest = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    manifest[entry["doc_id"]] = entry
                except:
                    continue
    return manifest

def save_manifest(manifest):
    """Save the document processing manifest."""
    # First backup the existing manifest
    if MANIFEST_PATH.exists():
        MANIFEST_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_BACKUP_PATH, "w", encoding="utf-8") as f_backup:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f_orig:
                f_backup.write(f_orig.read())
    
    # Now write the updated manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        for doc_id, entry in manifest.items():
            f.write(json.dumps(entry) + "\n")

def load_metadata():
    """Load the document metadata."""
    metadata = {}
    if METADATA_PATH.exists():
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    doc = json.loads(line)
                    if "doc_id" in doc:
                        metadata[doc["doc_id"]] = doc
                except:
                    continue
    return metadata

def save_metadata(metadata):
    """Save the document metadata."""
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        for doc_id, doc in metadata.items():
            f.write(json.dumps(doc) + "\n")

def save_summary(doc_id, summary_info):
    """Append summary information to summaries.jsonl"""
    summary_info["doc_id"] = doc_id
    summary_path = SUMMARY_DIR / "summaries.jsonl"
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary_info, ensure_ascii=False) + "\n")
    return str(summary_path)

def load_pdf_metadata(doc_id):
    """Load PDF metadata from the consolidated scraped_pdf_metadata.jsonl."""
    pdf_metadata_path = Path("data/pdf_metadata/scraped_pdf_metadata.jsonl")
    if not pdf_metadata_path.exists():
        return None
    with open(pdf_metadata_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                if record.get("doc_id") == doc_id:
                    record["full_text_path"] = f"data/pdf_full_text/{doc_id}.txt"
                    return record
            except:
                continue
    return None

def ask_gpt_summary_and_keywords(snippet, source_filename="", metadata_title="", committee=None, meeting_date=None):
    """Ask GPT to summarize and extract keywords from a document snippet."""
    prompt = f'''
You are an AI assistant helping to classify and summarize UK council documents.

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
                print(f"Error getting summary: {e}")
                return {"display_title": "", "summary": f"ERROR: {e}", "keywords": []}

def main():
    """Main function to summarize PDFs."""
    # Load manifest and metadata
    manifest = load_manifest()
    metadata = load_metadata()
    
    # Find all documents that have been scraped but not yet summarised
    docs_to_process = []
    for doc_id, entry in manifest.items():
        if entry.get("scraped", False) and not entry.get("summarised", False):
            docs_to_process.append(doc_id)
    
    print(f"Found {len(docs_to_process)} documents to summarize")
    
    processed_count = 0
    error_count = 0
    
    for doc_id in tqdm(docs_to_process, desc="Summarizing documents"):
        try:
            # Skip documents in excluded categories
            category = get_document_category(metadata.get(doc_id, {}).get("url", ""))
            if category.lower() in EXCLUDED_CATEGORIES:
                print(f"Skipping {doc_id} (excluded category: {category})")
                manifest[doc_id]["summarised"] = True
                manifest[doc_id]["timestamp"] = datetime.now().isoformat()
                continue

            # Skip if metadata text fields suggest EQIA
            metadata_text = json.dumps(metadata.get(doc_id, {})).lower()
            if "eqia" in metadata_text or "equality impact" in metadata_text:
                print(f"Skipping {doc_id} (metadata contains EQIA reference)")
                manifest[doc_id]["summarised"] = True
                manifest[doc_id]["timestamp"] = datetime.now().isoformat()
                continue
            
            # Get document metadata from file
            doc_metadata = load_pdf_metadata(doc_id)
            if not doc_metadata:
                print(f"No metadata file found for {doc_id}")
                # Try to get metadata path from manifest
                metadata_path = manifest[doc_id].get("metadata_path")
                if metadata_path and Path(metadata_path).exists():
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        doc_metadata = json.load(f)
                else:
                    raise Exception(f"No metadata available for {doc_id}")
            
            full_text_path = doc_metadata.get("full_text_path")
            if not full_text_path or not Path(full_text_path).exists():
                raise Exception(f"Full text not found for {doc_id}")
            
            # Read full text
            with open(full_text_path, "r", encoding="utf-8") as f:
                full_text = f.read()
            
            # Take a snippet for summarization
            words = full_text.strip().split()
            snippet = ' '.join(words[:min(MAX_WORDS, len(words))])
            
            # Extract metadata for summarization
            source_filename = doc_metadata.get("source_filename", "")
            metadata_title = doc_metadata.get("metadata_title", "")
            committee = metadata.get(doc_id, {}).get("committee_name", "")
            meeting_date = str(metadata.get(doc_id, {}).get("meeting_date", ""))
            
            # Get summary and keywords from GPT
            print(f"🤖 Summarizing: {doc_id}")
            gpt_response = ask_gpt_summary_and_keywords(
                snippet,
                source_filename=source_filename,
                metadata_title=metadata_title,
                committee=committee,
                meeting_date=meeting_date
            )

            # Skip if summary is missing or error
            if gpt_response.get("summary", "").startswith("ERROR"):
                raise Exception(f"OpenAI failed: {gpt_response.get('summary')}")

            # Create summary info object
            summary_info = {
                "summary": gpt_response.get("summary", ""),
                "keywords": gpt_response.get("keywords", []),
                "display_title": gpt_response.get("display_title", ""),
                "timestamp": datetime.now().isoformat(),
            }
            
            # Save summary to file
            save_summary(doc_id, summary_info)
            
            # Update metadata with summary
            if doc_id in metadata:
                metadata[doc_id].update({
                    "summary": gpt_response.get("summary", ""),
                    "keywords": gpt_response.get("keywords", []),
                    "display_title": gpt_response.get("display_title", ""),
                    "status": "complete",
                    "timestamp": datetime.now().isoformat(),
                })
            
            # Update manifest
            manifest[doc_id]["summarised"] = True
            manifest[doc_id]["timestamp"] = datetime.now().isoformat()
            
            processed_count += 1
            print(f"[✔] Summarized: {doc_id}")
            
            # Save the updates after each document to avoid losing work
            save_manifest(manifest)
            save_metadata(metadata)
            
            # Add delay to avoid API rate limits
            time.sleep(THROTTLE_SECONDS)
            
        except Exception as e:
            error_count += 1
            manifest[doc_id]["summarised"] = False
            manifest[doc_id]["error_msg"] = f"Summarization error: {str(e)}"
            print(f"❌ Error summarizing {doc_id}: {e}")
            
            # Save the manifest after each error
            save_manifest(manifest)
    
    # Save the updated manifest and metadata
    save_manifest(manifest)
    save_metadata(metadata)
    print(f"🎉 Finished summarizing. Processed: {processed_count}, Errors: {error_count}")

if __name__ == "__main__":
    main()
