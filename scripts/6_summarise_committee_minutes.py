import os
import json
from pathlib import Path
import openai
import pdfplumber
from tqdm import tqdm

# CONFIG
BASE_DIR = Path("data/council_documents")
METADATA_PATH = Path("data/planning_metadata.jsonl")
OPENAI_MODEL = "gpt-4o"
TEMPERATURE = 0.2
DRY_RUN = False
OVERWRITE = True

SYSTEM_PROMPT = """
You are a smart assistant that reads UK Planning Committee meeting minutes.

Extract and return structured JSON in this format:
{
  "meeting": {
    "committee": "Planning Applications Committee",
    "date": "YYYY-MM-DD",
    "location": "...",
    "chair": "...",
    "attendees": {
      "present": ["Name (Party)", "..."],
      "absent": ["..."],
      "virtual": []
    }
  },
  "motions": [
    {
      "item": "C1",
      "title": "...",
      "application_reference": "...",
      "proposed_by": "...",
      "seconded_by": "...",
      "full_text": "...",
      "outcome": "Carried | Refused | Deferred",
      "vote": {
        "for": null,
        "against": null,
        "abstain": null
      },
      "debate_summary": [
        "Key points made in support or opposition"
      ]
    }
  ],
  "summary": "A plain-English summary of the meeting outcome"
}

Do not guess missing details. Leave them blank or null.
Only include what is clearly stated or strongly implied.
"""

def is_planning_minutes(filepath):
    name = filepath.name.lower()
    return "minutes" in name and "planning" in str(filepath.parent).lower()

def extract_text(filepath):
    try:
        with pdfplumber.open(filepath) as pdf:
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    except Exception as e:
        print(f"❌ Failed to extract {filepath.name}: {e}")
        return None

def call_gpt(full_text):
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": full_text}
        ]
    )
    return response["choices"][0]["message"]["content"]

def load_existing_metadata():
    if not METADATA_PATH.exists():
        return {}
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return {json.loads(line)["meeting_id"]: line for line in f if line.strip()}

def write_metadata_store(records: dict):
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        for line in records.values():
            f.write(line.strip() + "\n")

def append_to_metadata(structured_obj, existing_records):
    mid = structured_obj["meeting_id"]
    record_line = json.dumps(structured_obj, ensure_ascii=False)
    if OVERWRITE or mid not in existing_records:
        existing_records[mid] = record_line
        print(f"✅ Stored record: {mid}")
    else:
        print(f"⚠️ Skipped (exists): {mid}")
    return existing_records

def main():
    planning_files = [p for p in BASE_DIR.rglob("*.pdf") if is_planning_minutes(p)]
    print(f"🔍 Found {len(planning_files)} planning minutes files.")

    if not planning_files:
        print("❌ No planning minutes found.")
        return

    existing = load_existing_metadata()

    for pdf_path in tqdm(planning_files, desc="Processing"):
        print(f"\n📄 Processing: {pdf_path.name}")
        text = extract_text(pdf_path)
        if not text:
            continue

        print(f"⏳ Sending {pdf_path.name} to GPT...")
        try:
            response_text = call_gpt(text)
            structured = json.loads(response_text)
            structured["meeting_id"] = str(pdf_path.relative_to(BASE_DIR))

            if DRY_RUN:
                print(json.dumps(structured, indent=2, ensure_ascii=False))
                continue

            existing = append_to_metadata(structured, existing)

        except Exception as e:
            print(f"❌ GPT failed on {pdf_path.name}: {e}")

    if not DRY_RUN:
        write_metadata_store(existing)
        print(f"\n🗂️ Metadata written to {METADATA_PATH}")

if __name__ == "__main__":
    main()
