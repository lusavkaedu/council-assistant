# pdf_processor/claude_scraping_script.py
# This script downloads PDFs and extracts their text content.

import os
import json
import random
import time
from datetime import datetime
from pathlib import Path
import requests
import fitz  # PyMuPDF
from tqdm import tqdm
import hashlib
import sys

# Dynamically add the project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))  # one level up
sys.path.append(project_root)

# === CONFIGURATION ===
METADATA_PATH = Path("data/metadata/documents.jsonl")
PDF_CACHE_DIR = Path("data/tmp_pdfs/")
PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
FULL_TEXT_DIR = Path("data/pdf_full_text/")
FULL_TEXT_DIR.mkdir(parents=True, exist_ok=True)
PDF_METADATA_DIR = Path("data/pdf_metadata/")
PDF_METADATA_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = Path("data/processed_register/pdf_manifest.jsonl")
MANIFEST_BACKUP_PATH = Path("data/processed_register/pdf_manifest_backup.jsonl")
WORK_HOURS = range(7, 22)  # 7am to 10pm
THROTTLE_SECONDS = (1, 5)  # Mimic human delays between requests

def download_pdf(url, doc_id):
    """Download a PDF from a URL and save it to the cache directory."""
    response = requests.get(url)
    if response.status_code == 200:
        pdf_path = PDF_CACHE_DIR / f"{doc_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        return pdf_path
    else:
        raise Exception(f"Failed to download PDF: {url}")

def is_work_hour():
    """Check if current time is within defined work hours."""
    now = datetime.now()
    return now.hour in WORK_HOURS and now.weekday() < 5  # Mon–Fri

def extract_pdf_text(pdf_path):
    """Extract all text from a PDF file."""
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
    """Extract metadata from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        doc.close()
        return {k: v for k, v in metadata.items() if v}  # remove empty values
    except Exception as e:
        return {"error": f"Metadata extraction failed: {e}"}

def count_tables(pdf_path):
    """Count the number of tables in a PDF file."""
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

def save_pdf_metadata(doc_id, metadata):
    """Append PDF metadata to a single JSONL file."""
    output_path = Path("data/pdf_metadata/scraped_pdf_metadata.jsonl")
    record = metadata["pdf_metadata"]
    record.update({
        "num_tables_detected": metadata.get("num_tables_detected"),
        "metadata_title": metadata.get("metadata_title"),
        "source_filename": metadata.get("source_filename"),
        "doc_id": doc_id
    })
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(output_path)

def load_pdf_metadata(doc_id):
    """Load PDF metadata from a file."""
    metadata_path = PDF_METADATA_DIR / f"{doc_id}.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def short_hash(value: str, length=6):
    """Generate a short hash from a string."""
    return hashlib.sha1(value.encode()).hexdigest()[:length]

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

def main():
    """Main function to scrape PDFs."""
    # Load manifest
    manifest = load_manifest()
    
    # Process documents from metadata
    processed_count = 0
    error_count = 0
    skipped_count = 0
    
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        documents = [json.loads(line) for line in f]
    
    for doc in tqdm(documents, desc="Scraping PDFs"):
        doc_id = doc.get("doc_id")
        if not doc_id:
            continue
        
        # Check if text file already exists
        full_text_path = FULL_TEXT_DIR / f"{doc_id}.txt"
        
        # Skip if already scraped and text file exists
        if doc_id in manifest and manifest[doc_id].get("scraped", False) and full_text_path.exists():
            print(f"[⏩] Skipping already scraped: {doc_id}")
            skipped_count += 1
            continue
            
        # If the text file exists but the manifest doesn't show it as scraped,
        # update the manifest without redownloading
        if full_text_path.exists():
            print(f"[📄] Text file exists for {doc_id}, updating manifest...")
            
            # Try to extract metadata from the PDF if it exists
            pdf_path = PDF_CACHE_DIR / f"{doc_id}.pdf"
            source_filename = os.path.basename(doc["url"])
            pdf_metadata = {"title": ""}  # Default empty metadata
            num_tables = -1
            
            # If PDF exists in cache, extract metadata
            if pdf_path.exists():
                pdf_metadata = extract_pdf_metadata(pdf_path)
                num_tables = count_tables(pdf_path)
            
            # Create metadata object
            doc_metadata = {
                "num_tables_detected": num_tables,
                "pdf_metadata": pdf_metadata,
                "source_filename": source_filename,
                "metadata_title": pdf_metadata.get("title", ""),
                "full_text_path": str(full_text_path),
            }
            
            # Save metadata to file
            metadata_path = save_pdf_metadata(doc_id, doc_metadata)
            
            # Update manifest
            if doc_id not in manifest:
                manifest[doc_id] = {
                    "doc_id": doc_id,
                    "scraped": True,
                    "summarised": False,
                    "chunked": False,
                    "embedded": False,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                manifest[doc_id]["scraped"] = True
                manifest[doc_id]["timestamp"] = datetime.now().isoformat()
            
            # Add the metadata reference to the manifest
            manifest[doc_id]["metadata_path"] = metadata_path
            
            processed_count += 1
            continue
            
        try:
            print(f"🔍 Downloading: {doc['url']}")
            source_filename = os.path.basename(doc["url"])
            pdf_path = download_pdf(doc["url"], doc_id)
            
            # Extract text and metadata
            full_text = extract_pdf_text(pdf_path)
            num_tables = count_tables(pdf_path)
            pdf_metadata = extract_pdf_metadata(pdf_path)
            
            # Save full text
            full_text_path = FULL_TEXT_DIR / f"{doc_id}.txt"
            with open(full_text_path, "w", encoding="utf-8") as f_text:
                f_text.write(full_text)
                
            # Create metadata object
            doc_metadata = {
                "num_tables_detected": num_tables,
                "pdf_metadata": pdf_metadata,
                "source_filename": source_filename,
                "metadata_title": pdf_metadata.get("title", ""),
                "full_text_path": str(full_text_path),
            }
            
            # Save metadata to file
            metadata_path = save_pdf_metadata(doc_id, doc_metadata)
                
            # Update manifest
            if doc_id not in manifest:
                manifest[doc_id] = {
                    "doc_id": doc_id,
                    "scraped": True,
                    "summarised": False,
                    "chunked": False,
                    "embedded": False,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                manifest[doc_id]["scraped"] = True
                manifest[doc_id]["timestamp"] = datetime.now().isoformat()
            
            # Add the metadata reference to the manifest
            manifest[doc_id]["metadata_path"] = metadata_path
            
            # Clean up the downloaded PDF
            if pdf_path.exists():
                pdf_path.unlink()
                
            processed_count += 1
            print(f"[✔] Processed: {doc_id}")
            
            # Save manifest after each successful processing to avoid losing work on interruption
            save_manifest(manifest)
            
            # Add a random delay to mimic human behavior
            delay = random.randint(*THROTTLE_SECONDS)
            print(f"🕒 Sleeping for {delay}s...")
            time.sleep(delay)
            
        except Exception as e:
            error_count += 1
            if doc_id not in manifest:
                manifest[doc_id] = {
                    "doc_id": doc_id,
                    "scraped": False,
                    "summarised": False,
                    "chunked": False,
                    "embedded": False,
                    "timestamp": datetime.now().isoformat()
                }
            manifest[doc_id]["error_msg"] = str(e)
            print(f"❌ Error: {doc_id} — {e}")
            
            # Save manifest after each error to avoid losing work on interruption
            save_manifest(manifest)
    
    # Save the updated manifest
    save_manifest(manifest)
    print(f"🎉 Finished scraping. Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}")

if __name__ == "__main__":
    main()
