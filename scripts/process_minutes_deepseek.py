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

INPUT_DIR = "/Users/lgfolder/Downloads/data scrape full 1 page only/full_council/2025-03-13"
OUTPUT_DIR = "/Users/lgfolder/Downloads/minutes_processed"
MINUTES_KEYWORD = "minutes"
FIRST_PAGE_CHECK_LIMIT = 2000  # Characters

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Suppress pdfminer noise
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# Load spaCy model
print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

# Initialize YAKE
kw_extractor = yake.KeywordExtractor(
    lan="en", n=1, dedupLim=0.9, top=10, features=None
)

# -------------------- Functions --------------------

def extract_keywords(text):
    keywords = kw_extractor.extract_keywords(text)
    return [kw for kw, _ in keywords]

def extract_attendance_info(text):
    info = {"present": [], "absent": [], "virtual": []}

    present_match = re.search(r"PRESENT:\s+(.*?)(?=\n\n|\nIN ATTENDANCE|\n\d+\.\s)", text, re.DOTALL | re.IGNORECASE)
    if present_match:
        names = re.split(r",\s*", present_match.group(1).strip())
        info["present"] = [name.strip() for name in names if name]

    apologies_match = re.search(r"apologies from ([^\.]+)\.", text, re.IGNORECASE)
    if apologies_match:
        names = re.split(r",\s*", apologies_match.group(1).strip().rstrip('.'))
        info["absent"] = [name.strip() for name in names if name]

    virtual_match = re.findall(r"(\b(?:Mr|Mrs|Ms|Miss|Dr)\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+.*?attending the meeting virtually", text, re.IGNORECASE)
    info["virtual"] = list(set(virtual_match))

    return info

def get_chairman(text):
    match = re.search(r"(Mr|Mrs|Ms|Miss|Dr)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*\(Chairman\)", text, re.IGNORECASE)
    return match.group(0) if match else "unknown"

def extract_motions(text):
    motions = []
    lines = text.splitlines()
    current_motion = None
    motion_lines = []
    vote_pattern = re.compile(r"vote.*?as follows:\s+For\s+\((\d+)\).*?Against\s+\((\d+)\).*?Abstain\s+\((\d+)\)", re.IGNORECASE)

    recent_votes = []

    for i, line in enumerate(lines):
        if re.search(r"\bproposed\b.*?\bseconded\b", line, re.IGNORECASE):
            if current_motion:
                if recent_votes:
                    vote_result = recent_votes.pop(0)
                    if vote_result["for"] > 0 and vote_result["against"] == 0 and vote_result["abstain"] == 0:
                        outcome = "Unanimous"
                    elif vote_result["for"] > vote_result["against"]:
                        outcome = "Passed"
                    else:
                        outcome = "Failed"
                    current_motion["vote_result"] = vote_result
                    current_motion["outcome"] = outcome
                motions.append(current_motion)
            proposer_search = re.search(r"(Mr|Mrs|Ms|Dr)\s+[A-Z][a-z]+.*?\sproposed", line)
            seconder_search = re.search(r"and\s+(Mr|Mrs|Ms|Dr)\s+[A-Z][a-z]+.*?\sseconded", line)
            proposer = proposer_search.group(0) if proposer_search else None
            seconder = seconder_search.group(0) if seconder_search else None
            current_motion = {
                "proposer": proposer,
                "seconder": seconder,
                "text": "",
                "vote_result": None,
                "outcome": "Unknown"
            }
            motion_lines = []
        elif current_motion is not None:
            if line.strip() == "" or re.match(r"\d{3}\.", line):
                current_motion["text"] = " ".join(motion_lines).strip()
                if recent_votes:
                    vote_result = recent_votes.pop(0)
                    if vote_result["for"] > 0 and vote_result["against"] == 0 and vote_result["abstain"] == 0:
                        outcome = "Unanimous"
                    elif vote_result["for"] > vote_result["against"]:
                        outcome = "Passed"
                    else:
                        outcome = "Failed"
                    current_motion["vote_result"] = vote_result
                    current_motion["outcome"] = outcome
                motions.append(current_motion)
                current_motion = None
            else:
                motion_lines.append(line.strip())

        vote_match = vote_pattern.search(line)
        if vote_match:
            recent_votes.append({
                "for": int(vote_match.group(1)),
                "against": int(vote_match.group(2)),
                "abstain": int(vote_match.group(3)),
            })

    if current_motion:
        current_motion["text"] = " ".join(motion_lines).strip()
        motions.append(current_motion)

    return motions

def extract_entities(doc):
    entities = defaultdict(list)
    for ent in doc.ents:
        entities[ent.label_].append(ent.text)

    org_exclude = {"OBE", "MBE", "Appendix", "Council", "Budget", "Agenda"}
    entities["ORG"] = [e for e in entities["ORG"] if e not in org_exclude and len(e) > 3]

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
    try:
        with pdfplumber.open(filepath) as pdf:
            texts = []
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        texts.append(text)
                except Exception as page_err:
                    print(f"⚠️ Failed to extract text from page {i+1} in {filepath.name}: {page_err}")
            return "\n".join(texts)
    except Exception as e:
        raise RuntimeError(f"Unable to open or read {filepath.name}: {e}")

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

        chair = get_chairman(text)
        num_attendees = len(attendance.get("present", []))
        num_absent = len(attendance.get("absent", []))
        num_virtual = len(attendance.get("virtual", []))
        resolutions = metadata["resolutions"][:2]
        num_motions = len(motions)
        motion_outcomes = [m["outcome"] for m in motions if m.get("outcome")]
        outcome_counts = {o: motion_outcomes.count(o) for o in set(motion_outcomes)}
        motion_summary = ", ".join(f"{k}: {v}" for k, v in outcome_counts.items())

        summary = (
            f"Meeting chaired by {chair} with {num_attendees} attendees "
            f"({num_virtual} virtual). {num_absent} apologies. "
            f"{num_motions} motions considered ({motion_summary}). "
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
    pdf_files = [f for f in Path(input_dir).rglob("*.pdf") if "minutes" in f.name.lower()]
    print(f"🔍 Found {len(pdf_files)} PDF files. Starting processing...")

    output_jsonl_path = Path(output_dir) / "ALL_MINUTES.jsonl"

    # Clear the .jsonl file if it exists
    if output_jsonl_path.exists():
        output_jsonl_path.unlink()

    processed_count = 0

    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        result = process_file(pdf_path)
        if result:
            # Save individual JSON
            individual_path = Path(output_dir) / f"{pdf_path.stem}.json"
            with open(individual_path, 'w') as f:
                json.dump(result, f, indent=2)

            # Append to .jsonl file
            with open(output_jsonl_path, 'a') as f:
                f.write(json.dumps(result) + '\n')

            processed_count += 1

    print(f"\n✅ Done. {processed_count} minutes files processed. Results saved to:\n{output_dir}")

# -------------------- Run --------------------

if __name__ == "__main__":
    process_all_files(INPUT_DIR, OUTPUT_DIR)
