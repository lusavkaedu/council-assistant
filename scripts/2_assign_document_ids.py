import hashlib
import os
import uuid
import json
from pathlib import Path
from PyPDF2 import PdfReader  # Using PyPDF2 to read PDF content
from difflib import SequenceMatcher

def are_filenames_similar(name1, name2, threshold=0.85):
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio() >= threshold

# CONFIGURATION
BASE_DIR = Path('data/council_documents')
REGISTER_PATH = Path('data/processed_register/document_ids.json')

# Load existing register if available
if REGISTER_PATH.exists():
    with open(REGISTER_PATH, 'r', encoding='utf-8') as f:
        doc_register = json.load(f)
else:
    doc_register = {}

# Function to generate document IDs based on file path
def generate_doc_id(file_path):
    unique_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(file_path))
    return f"doc_{unique_id.hex[:8]}"  # Shorten to first 8 characters

# Function to generate a hash based on the content of the PDF
def generate_doc_hash(file_path):
    hash_sha256 = hashlib.sha256()  # Using SHA-256 hash
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    hash_sha256.update(text.encode('utf-8'))  # Update hash with the page text
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

# Collect all PDF paths from 'originals' folders
def collect_pdf_paths():
    pdfs = []
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.lower().endswith('.pdf'):
                full_path = Path(root) / file
                if "originals" in str(full_path):  # Only target PDFs in 'originals'
                    pdfs.append(full_path)
    return pdfs

# Assign document IDs and hashes, and save to register
def assign_ids_to_pdfs():
    all_pdfs = collect_pdf_paths()
    for pdf_path in all_pdfs:
        rel_path = pdf_path.relative_to(BASE_DIR)
        # If no doc_id already exists, generate and assign one
        if str(rel_path) not in doc_register:
            doc_hash = generate_doc_hash(pdf_path)
            if doc_hash:
                # Search for existing doc_id with same hash and similar filename
                existing_match = None
                current_name = rel_path.name
                for existing_path, info in doc_register.items():
                    if info["hash"] == doc_hash:
                        existing_name = Path(existing_path).name
                        if are_filenames_similar(current_name, existing_name):
                            existing_match = info["id"]
                            break

                if existing_match:
                    doc_id = existing_match
                else:
                    doc_id = generate_doc_id(rel_path)

                doc_register[str(rel_path)] = {"id": doc_id, "hash": doc_hash}
                manifest_path = Path("data/processed_register/document_manifest.jsonl")
                parts = rel_path.parts
                if len(parts) >= 4 and parts[2] == "originals":
                    committee = parts[0]
                    meeting_date = parts[1]
                    filename = parts[3]
                    manifest_entry = {
                        "doc_id": doc_id,
                        "relative_path": str(rel_path),
                        "committee": committee,
                        "meeting_date": meeting_date,
                        "filename": filename,
                        "status": "ready_for_chunking",
                        "hash": doc_hash,
                        "source": "scraper"
                    }
                    with open(manifest_path, "a", encoding="utf-8") as mf:
                        mf.write(json.dumps(manifest_entry) + "\n")
                print(f"Assigned ID {doc_id} and Hash to {rel_path}")
            else:
                print(f"Failed to generate hash for {rel_path}")
        else:
            print(f"ID already assigned to {rel_path}")

    # Save the updated register
    with open(REGISTER_PATH, 'w', encoding='utf-8') as f:
        json.dump(doc_register, f, indent=2, ensure_ascii=False)

# Run the function
if __name__ == "__main__":
    assign_ids_to_pdfs()
    print("✅ Document IDs and hashes assigned and saved.")