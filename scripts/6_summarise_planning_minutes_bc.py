import os
import json
from pathlib import Path
import openai
import pdfplumber
from tqdm import tqdm

# CONFIG
BASE_DIR = Path("data/council_documents")
METADATA_PATH = Path("data/planning_metadata.jsonl")
OPENAI_MODEL = "gpt-4o-mini"
TEMPERATURE = 0.2
SYSTEM_PROMPT = """
You are a smart assistant that reads local UK Planning Committee meeting minutes.
Return structured JSON in the following schema:
{
  "meeting_id": "...",
  "committee": "...",
  "meeting_date": "...",
  "location": "...",
  "chair": "...",
  "attendance": {
    "present": [...],
    "absent": [...],
    "virtual": []
  },
  "applications": [...],
  "appeals_noted": true,
  "summary": "..."
}
Be accurate. If you are unsure of a field, leave it blank or empty list.
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

def append_to_metadata(json_obj):
    with open(METADATA_PATH, "a") as f:
        f.write(json.dumps(json_obj) + "\n")

def main():
    planning_files = [p for p in BASE_DIR.rglob("*.pdf") if is_planning_minutes(p)]
    print(f"🔍 Found {len(planning_files)} planning minutes files.")

    if not planning_files:
        print("❌ No planning minutes found.")
        return

    pdf_path = planning_files[0]
    print(f"📄 Processing: {pdf_path.name}")
    text = extract_text(pdf_path)
    if not text:
        return

    print(f"⏳ Sending {pdf_path.name} to GPT...")
    try:
        response_json = call_gpt(text)
        structured = json.loads(response_json)
        append_to_metadata(structured)
        print(f"✅ Appended {structured.get('meeting_id', 'unknown')} to metadata.")
    except Exception as e:
        print(f"❌ GPT failed on {pdf_path.name}: {e}")

if __name__ == "__main__":
    main()
