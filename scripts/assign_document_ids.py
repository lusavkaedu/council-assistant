import json
import hashlib
from pathlib import Path

# === CONFIGURATION ===
base_dir = Path("data/council_documents")
register_path = Path("data/processed_register/document_ids.json")

# === Load or initialize register ===
if register_path.exists():
    with open(register_path) as f:
        doc_register = json.load(f)
else:
    doc_register = {}

# === Function to calculate file hash ===
def calculate_sha256(filepath):
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

# === Scan PDFs and update register ===
new_entries = 0
for pdf_path in base_dir.rglob("*.pdf"):
    try:
        rel_path = str(pdf_path.relative_to(base_dir))
    except ValueError:
        continue  # skip files not under base_dir

    file_hash = calculate_sha256(pdf_path)

    if rel_path not in doc_register or doc_register[rel_path]["hash"] != file_hash:
        doc_id = f"doc_{hashlib.md5(rel_path.encode()).hexdigest()[:12]}"
        doc_register[rel_path] = {
            "id": doc_id,
            "hash": file_hash
        }
        new_entries += 1

# === Save updated register ===
register_path.parent.mkdir(parents=True, exist_ok=True)
with open(register_path, "w") as f:
    json.dump(doc_register, f, indent=2)

print(f"✅ Assigned document_ids to {new_entries} new PDFs.")
print(f"📁 Register saved to {register_path}")
print(f"📊 Total registered documents: {len(doc_register)}")