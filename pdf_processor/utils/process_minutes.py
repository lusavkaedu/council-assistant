import os
import re
import json
import logging
from pathlib import Path
from collections import defaultdict

import pdfplumber
import spacy
import yake
from tqdm import tqdm

# -------------------- Setup --------------------

OUTPUT_DIR = "minutes_processed"
INPUT_DIR = "minutes_input"
MINUTES_KEYWORD = "minutes"
FIRST_PAGE_CHECK_LIMIT = 2000

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)

logging.getLogger("pdfminer").setLevel(logging.ERROR)

print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

kw_extractor = yake.KeywordExtractor(
    lan="en", n=1, dedupLim=0.9, top=10, features=None
)

def extract_keywords(text):
    keywords = kw_extractor.extract_keywords(text)
    return [kw for kw, _ in keywords]

def extract_attendance_info(text):
    info = {"present": [], "absent": [], "virtual": []}

    present_match = re.search(r"PRESENT:\s+(.*?)(?=\n\n|\nIN ATTENDANCE|\n\d+\.\s)", text, re.DOTALL | re.IGNORECASE)
    if present_match:
        names = re.split(r",\s*", present_match.group(1).strip())
        info["present"] = [name.strip() for name in names if name]

    apologies_match = re.search(r"apologies from (.*?)(?=\n\n|\n\(?\d+\)\s|\n\s*\w+:|\n\w+\s+declared|\n\n)", text, re.DOTALL | re.IGNORECASE)
    if apologies_match:
        names = re.split(r",\s*", apologies_match.group(1).strip().rstrip('.'))
        info["absent"] = [name.strip() for name in names if name]

    virtual_match = re.findall(r"(\b(?:Mr|Mrs|Ms|Miss|Dr)\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+.*?attending the meeting virtually", text, re.IGNORECASE)
    info["virtual"] = list(set(virtual_match))

    return info

def extract_motions(text):
    motions = []
    motion_blocks = re.findall(
        r"(?:Mr|Mrs|Ms|Dr)\s+[A-Z][a-z]+.*?\sproposed.*?\n+(.+?)(?=(?:\n\([0-9]+\) Following the debate|Amendment lost|Motion carried|Substantive Motion Carried))",
        text, re.DOTALL | re.IGNORECASE
    )

    vote_blocks = re.findall(
        r"vote.*?as follows:\s+For\s+\((\d+)\).*?Against\s+\((\d+)\).*?Abstain\s+\((\d+)\)", text, re.DOTALL | re.IGNORECASE
    )

    for i, motion_text in enumerate(motion_blocks):
        motion_text = motion_text.strip().replace("\n", " ")
        result = vote_blocks[i] if i < len(vote_blocks) else None
        outcome = "Passed" if result and int(result[0]) > int(result[1]) else "Failed"
        motions.append({
            "text": motion_text,
            "vote_result": {
                "for": int(result[0]) if result else None,
                "against": int(result[1]) if result else None,
                "abstain": int(result[2]) if result else None
            } if result else None,
            "outcome": outcome if result else "Unknown"
        })
    return motions

def extract_entities(doc):
    entities = defaultdict(list)
    for ent in doc.ents:
        entities[ent.label_].append(ent.text)

    resolutions = re.findall(r"RESOLVED that (.+?)(?=\n|$)", doc.text, re.IGNORECASE)
    if resolutions:
        entities["RESOLUTION"] = resolutions

    attendees = re.search(r"PRESENT: (.+?)(?=\n\n|\n\w+:|$)", doc.text, re.DOTALL)
    if attendees:
        entities["ATTENDEES"] = [a.strip() for a in attendees.group(1).split(",")]

    return dict(entities)

def is_minutes_file(filepath, first_page_text):
    filename = str(filepath).lower()
    first_page = first_page_text[:FIRST_PAGE_CHECK_LIMIT].lower()
    return (MINUTES_KEYWORD in filename) or (MINUTES_KEYWORD in first_page)

def extract_text_from_pdf(filepath):
    with pdfplumber.open(filepath) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def process_file(filepath):
    try:
        text = extract_text_from_pdf(filepath)
        if not text:
            raise ValueError("Empty or unreadable first page")

        attendance = extract_attendance_info(text)
        motions = extract_motions(text)

        if not is_minutes_file(filepath.name, text):
            return None

        doc = nlp(text)

        metadata = {
            "filepath": str(filepath),
            "entities": extract_entities(doc),
            "keywords": extract_keywords(text),
            "resolutions": list(set(re.findall(r"RESOLVED that (.+?)(?=\n|$)", text, re.I))),
            "motions": motions,
            "attendance": attendance,
        }

        chair = metadata["entities"].get("PERSON", ["unknown"])[0]
        num_attendees = len(attendance.get("present", []))
        num_absent = len(attendance.get("absent", []))
        num_virtual = len(attendance.get("virtual", []))
        resolutions = metadata["resolutions"][:2]
        num_motions = len(motions)

        summary = (
            f"Meeting chaired by {chair} with {num_attendees} attendees "
            f"({num_virtual} virtual). {num_absent} apologies. "
            f"{num_motions} motions considered. "
            f"Key resolutions: {'; '.join(resolutions) if resolutions else 'None recorded'}."
        )

        return {
            "metadata": metadata,
            "summary": summary
        }

    except Exception as e:
        print(f"❌ Error processing {filepath}:\n  {e}")
        return None

def process_all_files(input_dir, output_dir):
    pdf_files = list(Path(input_dir).rglob("*.pdf"))
    print(f"🔍 Found {len(pdf_files)} PDF files. Starting processing...")

    output_jsonl_path = Path(output_dir) / "ALL_MINUTES.jsonl"

    if output_jsonl_path.exists():
        output_jsonl_path.unlink()

    processed_count = 0

    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        result = process_file(pdf_path)
        if result:
            individual_path = Path(output_dir) / f"{pdf_path.stem}.json"
            with open(individual_path, 'w') as f:
                json.dump(result, f, indent=2)
            with open(output_jsonl_path, 'a') as f:
                f.write(json.dumps(result) + '\n')
            processed_count += 1

    print(f"\n✅ Done. {processed_count} minutes files processed. Results saved to:\n{output_dir}")

if __name__ == "__main__":
    process_all_files(INPUT_DIR, OUTPUT_DIR)