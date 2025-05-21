#pdf_processor/utils/classify_pdfs.py
# This script resets the "status" field to "pending" for any document marked "error" in your documents_test.jsonl. This lets you retry only the failed ones.

import json
from pathlib import Path

INPUT_PATH = Path("data/metadata/documents_test.jsonl")
OUTPUT_PATH = Path("data/metadata/documents_test_review.jsonl")

with open(INPUT_PATH, "r", encoding="utf-8") as f_in, open(OUTPUT_PATH, "w", encoding="utf-8") as f_out:
    for line in f_in:
        doc = json.loads(line)
        if doc.get("status") == "error":
            doc["status"] = "pending"
            doc.pop("error_msg", None)  # optional: remove old error message
        f_out.write(json.dumps(doc, ensure_ascii=False) + "\n")

print("✅ Reset complete. Saved to documents_test_reset.jsonl")