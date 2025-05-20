# 0_scraped_meetings_cleaner.py

import pandas as pd
from pathlib import Path
import sys
from pathlib import Path
import re

# Ensure root folder is on the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.documents import get_document_category

# === CONFIG ===
INPUT_PATH = Path("data/meetings/kcc_meetings.jsonl")
MEETINGS_OUT = Path("data/metadata/meetings.jsonl")
AGENDAS_OUT = Path("data/metadata/agendas.jsonl")
DOCS_OUT = Path("data/metadata/documents.jsonl")

# === Load ===
data = pd.read_json(INPUT_PATH, lines=True)
initial_count = len(data)

# === 1. Clean Meeting Metadata ===
data = data.drop_duplicates(subset="web_meeting_code", keep="last")
after_dedup = len(data)
print(f"[INFO] Dropped {initial_count - after_dedup} duplicate meeting entries. Remaining: {after_dedup}")

data['meeting_date'] = pd.to_datetime(data['meeting_date'], errors='coerce')
before_date_drop = len(data)
data = data.dropna(subset=['meeting_date'])
after_date_drop = len(data)
print(f"[INFO] Dropped {before_date_drop - after_date_drop} rows with invalid or missing meeting dates. Remaining: {after_date_drop}")

before_error_drop = len(data)
data = data[data["error"].isna()]
after_error_drop = len(data)
print(f"[INFO] Dropped {before_error_drop - after_error_drop} meetings with non-null error field. Remaining: {after_error_drop}")

# === 2. Preprocess Agenda Items ===

PDF_PATTERN = re.compile(r'\s*PDF\s*\d+(\.\d+)?\s*(KB|MB)', flags=re.IGNORECASE)

def clean_item_title(title):
    if isinstance(title, str):
        return PDF_PATTERN.sub('', title).strip()
    return title

def clean_agenda_items(items):
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and 'item_title' in item:
                item['item_title'] = clean_item_title(item['item_title'])
    return items

data['agenda_items'] = data['agenda_items'].apply(clean_agenda_items)

# === 3. Flatten Agenda Items ===

def flatten_agenda_items(df):
    df = df.explode('agenda_items').dropna(subset=['agenda_items']).copy()
    agenda = pd.json_normalize(df['agenda_items'])
    for col in ['meeting_id', 'committee_name', 'meeting_date', 'web_meeting_code', 'pdf_attachment_ok', 'attached_pdfs']:
        agenda[col] = df[col].values if col in df else None
    agenda['sub_items'] = agenda.get('sub_items', None)
    agenda = agenda.explode('sub_items')
    agenda['sub_item_content'] = agenda['sub_items'].apply(lambda x: x.get('title') if isinstance(x, dict) else None)
    agenda['item_text'] = agenda['sub_items'].apply(lambda x: x.get('content') if isinstance(x, dict) else None)
    agenda['item_text'] = agenda['item_text'].fillna(agenda.get('content', ''))
    agenda['pdf_urls'] = agenda.apply(
        lambda row: row['sub_items'].get('pdf_urls') if isinstance(row['sub_items'], dict) and row['sub_items'].get('pdf_urls') else row.get('pdf_urls', []),
        axis=1
    )
    return agenda[[
        'meeting_id', 'committee_name', 'meeting_date', 'web_meeting_code',
        'item_number', 'item_title', 'item_text', 'pdf_urls', 'sub_item_content'
    ]].copy()

agenda_items = flatten_agenda_items(data).reset_index(drop=True)
agenda_items['agenda_id'] = agenda_items.apply(lambda row: f"{row['meeting_id']}__{str(row.name).zfill(4)}", axis=1)
agenda_items['item_title'] = agenda_items['item_title'].fillna('').apply(clean_item_title)

def remove_pdf_lines(text):
    if not isinstance(text, str):
        return text
    return "\n".join([line for line in text.splitlines() if '.pdf' not in line.lower()]).strip()

agenda_items['item_text'] = agenda_items['item_text'].apply(remove_pdf_lines)
agenda_items['word_count'] = agenda_items['item_text'].fillna('').apply(lambda x: len(str(x).split()))
agenda_items['pdf_count'] = agenda_items['pdf_urls'].apply(lambda x: len(x) if isinstance(x, list) else 0)

# === 4. Categorise Agenda Items ===

CATEGORY_PATTERNS = [
    ('webcast', re.compile(r'\bWebcast for\b', re.IGNORECASE)),
    ('apologies', re.compile(r'\bapologies\b', re.IGNORECASE)),
    ('declarations', re.compile(r'declaration[s]? of (interest|disclosable|inter)', re.IGNORECASE)),
    ('next_meeting', re.compile(r'date of next meeting', re.IGNORECASE)),
    ('exempt_items', re.compile(r'exempt |THE PRESS AND PUBLIC', re.IGNORECASE)),
    ('work_programme', re.compile(r'work programme', re.IGNORECASE)),
    ('future_meeting', re.compile(r'future meeting|Date of next', re.IGNORECASE)),
    ('introduction', re.compile(r'^introduction', re.IGNORECASE)),
    ('substitutes', re.compile(r'substitutes', re.IGNORECASE)),
    ('questions', re.compile(r'questions', re.IGNORECASE)),
    ('appeal', re.compile(r'appeal ', re.IGNORECASE)),
    ('minutes', re.compile(r'minutes', re.IGNORECASE)),
    ('appointments', re.compile(r'appointment', re.IGNORECASE)),
    ('restricted_items', re.compile(r'restricted', re.IGNORECASE)),
    ('election', re.compile(r'election of', re.IGNORECASE)),
    ('pay_policy', re.compile(r'pay policy', re.IGNORECASE)),
    ('welcome', re.compile(r'welcome', re.IGNORECASE)),
    ('procedural', re.compile(r'MATTERS FOR DECISION| dates', re.IGNORECASE)),
    ('performance', re.compile(r'performance report', re.IGNORECASE)),
]

def classify_category(title):
    title = str(title).lower().strip()
    for label, pattern in CATEGORY_PATTERNS:
        if pattern.search(title):
            return label
    return "discussion"

agenda_items['category'] = agenda_items['item_title'].apply(classify_category)

# === 5. Calculate PDF stats ===

all_pdfs = [url for urls in agenda_items['pdf_urls'] if isinstance(urls, list) for url in urls]

header_pdfs = []
for m in data.to_dict(orient="records"):
    if 'header_pdf_urls' in m and isinstance(m['header_pdf_urls'], list):
        header_pdfs.extend(m['header_pdf_urls'])

pdf_series = pd.Series(all_pdfs + header_pdfs)

total_pdfs = pdf_series.size
unique_pdfs = pdf_series.nunique()
duplicate_pdfs = total_pdfs - unique_pdfs

print(f"[INFO] Total PDF URLs extracted: {total_pdfs}")
print(f"[INFO] Unique PDF URLs: {unique_pdfs}")
print(f"[INFO] Duplicate PDF URLs: {duplicate_pdfs}")

# Calculate assigned and unassigned header PDFs here for later use
assigned_pdfs = set(all_pdfs)
unassigned_headers = [url for url in header_pdfs if url not in assigned_pdfs]

#
# === 6. Add fallback agenda items for unassigned header PDFs ===
fallback_agendas = []

for i, url in enumerate(unassigned_headers):
    meeting = next((m for m in data.to_dict(orient="records") if url in m.get("header_pdf_urls", [])), {})
    fallback_agendas.append({
        "meeting_id": meeting.get("meeting_id", "unknown"),
        "committee_name": meeting.get("committee_name", "Unassigned"),
        "meeting_date": meeting.get("meeting_date", None),
        "web_meeting_code": meeting.get("web_meeting_code", None),
        "item_number": f"F{i+1}",
        "item_title": "Unlinked Document",
        "item_text": "",
        "pdf_urls": [url],
        "sub_item_content": None,
        "agenda_id": f"{meeting.get('meeting_id', 'fallback')}__F{i+1}",
        "word_count": 0,
        "pdf_count": 1,
        "category": "unassigned",
        "embed_status": False,
        "doc_ids": [],
        "missing_doc": True
    })

# Append fallback agenda items before building url_to_agenda
if fallback_agendas:
    fallback_df = pd.DataFrame(fallback_agendas)
    # Remove any all-NA columns, then all-NA rows
    fallback_df = fallback_df.dropna(axis=1, how='all')  # Remove all-NA columns
    fallback_df = fallback_df.dropna(how='all')          # Then remove all-NA rows
    if not fallback_df.empty:
        agenda_items = pd.concat([agenda_items, fallback_df], ignore_index=True)
agenda_items = agenda_items.reset_index(drop=True)

# === 7.Build a lookup of url → agenda_id ===
url_to_agenda = {}
for _, row in agenda_items.iterrows():
    for url in row.get("pdf_urls", []):
        url_to_agenda[url.strip().lower()] = row["agenda_id"]

# === 8.Assign embed_status ===
def should_embed(row):
    category = row.get("category", "")
    wc = row.get("word_count", 0)
    text = str(row.get("item_text", "")).lower()
    has_pdf = isinstance(row.get("pdf_urls"), list) and len(row["pdf_urls"]) > 0

    if category == "discussion":
        return True
    if category == "appointments":
        return wc > 10
    if category == "questions":
        return wc > 20 or has_pdf
    if category == "work_programme":
        return True
    if category == "appeal":
        return wc > 5 and "restricted" in text
    if category == "declarations":
        return wc > 50
    return False

agenda_items["embed_status"] = agenda_items.apply(should_embed, axis=1)


# === 9. Build Document Metadata ===
doc_rows = []

for _, row in agenda_items.iterrows():
    urls = row.get("pdf_urls", [])
    if not isinstance(urls, list):
        continue

    for url in urls:
        url = url.strip().split("#")[0]
        doc_rows.append({
            "url": url,
            "meeting_id": row["meeting_id"],
            "agenda_id": url_to_agenda.get(url.strip().lower()),
            "committee_name": row["committee_name"],
            "committee_id": "",
            "meeting_date": int(row["meeting_date"].timestamp() * 1000) if pd.notnull(row["meeting_date"]) else None,
            "item_title": row["item_title"],
            "doc_id": "",  # assigned later using assign_doc_ids()
            "doc_category": get_document_category(url.split("/")[-1]),
            "status": "pending"
        })

# === 10. Add unassigned header PDFs to document metadata ===
for url in unassigned_headers:
    meeting = next(
        (m for m in data.to_dict(orient="records") if url in m.get("header_pdf_urls", [])), None
    )
    doc_rows.append({
        "url": url,
        "meeting_id": meeting["meeting_id"] if meeting else "unknown",
        "agenda_id": url_to_agenda.get(url.strip().lower()),
        "committee_name": meeting["committee_name"] if meeting else "Unassigned",
        "committee_id": "",
        "meeting_date": int(pd.to_datetime(meeting["meeting_date"]).timestamp() * 1000) if meeting and pd.notnull(meeting["meeting_date"]) else None,
        "item_title": "Header-only document",
        "doc_id": "",  # assigned later
        "doc_category": get_document_category(url.split("/")[-1]),
        "status": "pending"
    })


# === 11. Save Outputs ===
data.to_json(MEETINGS_OUT, orient="records", lines=True)
agenda_items.to_json(AGENDAS_OUT, orient="records", lines=True)

print(f"✅ Saved cleaned meetings: {MEETINGS_OUT}")
print(f"✅ Saved flattened agendas: {AGENDAS_OUT}")

documents_df = pd.DataFrame(doc_rows)
documents_df = documents_df.drop_duplicates(subset="url", keep="first")
documents_df.to_json(DOCS_OUT, orient="records", lines=True)
print(f"✅ Saved documents metadata: {DOCS_OUT}")

# === 12. Assign doc_ids ===

sample_docs = pd.read_json(DOCS_OUT, lines=True)

# --- Inline assign_doc_ids and helpers ---
import hashlib
from datetime import datetime
import jsonlines
import json
from tqdm import tqdm

def short_hash(value: str, length=6) -> str:
    return hashlib.sha1(value.encode()).hexdigest()[:length]

def generate_doc_id(doc, council_code="kcc", scope="cc") -> str:
    timestamp = doc.get("meeting_date")
    if not timestamp:
        date_str = "unknown-date"
    else:
        date_str = pd.to_datetime(timestamp, unit='ms').strftime("%Y-%m-%d")
    base = doc.get("url", "") + doc.get("item_title", "")
    return f"{council_code}_{scope}_{date_str}_{short_hash(base)}"

def assign_doc_ids(register_path=Path("data/processed_register/document_ids.json"),
                   raw_path=Path("data/metadata/documents.jsonl"),
                   base_dir=Path(".")):
    if register_path.exists():
        with register_path.open("r", encoding="utf-8") as f:
            doc_register = json.load(f)
    else:
        doc_register = {}

    with jsonlines.open(raw_path, "r") as reader:
        metadata = list(reader)

    updated_metadata = []
    for entry in tqdm(metadata, desc="🪪 Assigning doc_ids", unit="file"):
        doc_id = entry.get("doc_id")
        if not doc_id:
            doc_id = generate_doc_id(entry)
        entry["doc_id"] = doc_id
        key = entry.get("url", "") or entry.get("path", "")
        if key:
            doc_register[key] = {"id": doc_id}
        updated_metadata.append(entry)

    with jsonlines.open(raw_path, "w") as writer:
        for entry in updated_metadata:
            writer.write(entry)

    with register_path.open("w", encoding="utf-8") as f:
        json.dump(doc_register, f, indent=2, ensure_ascii=False)

# --- End inline assign_doc_ids and helpers ---

assign_doc_ids()


sample_docs_after = pd.read_json(DOCS_OUT, lines=True)
print("✅ Assigned doc_ids and updated document register")

# === 13. Link doc_ids back to agenda items ===
import json
with open("data/processed_register/document_ids.json", "r", encoding="utf-8") as f:
    doc_id_map = json.load(f)

def get_doc_ids(pdf_urls):
    ids = []
    for url in pdf_urls:
        match = doc_id_map.get(url)
        if match and "id" in match:
            ids.append(match["id"])
    return ids if ids else None

agenda_items["doc_ids"] = agenda_items["pdf_urls"].apply(get_doc_ids)

# Optionally overwrite the agendas file with enriched doc_ids
agenda_items.to_json(AGENDAS_OUT, orient="records", lines=True)
print(f"✅ Updated agendas with doc_ids: {AGENDAS_OUT}")

# === Unassigned header PDFs ===
# assigned_pdfs and unassigned_headers are already defined above

# === 14. Tag agenda items missing doc_ids ===
agenda_items['missing_doc'] = agenda_items['doc_ids'].isnull()

# === Final counts ===
print(f"📄 meetings.jsonl: {MEETINGS_OUT} — {data.shape[0]} rows")
print(f"📄 agendas.jsonl: {AGENDAS_OUT} — {agenda_items.shape[0]} rows")

if DOCS_OUT.exists():
    with open(DOCS_OUT, "r", encoding="utf-8") as f:
        num_docs = sum(1 for _ in f)
    print(f"📄 documents.jsonl: {DOCS_OUT} — {num_docs} rows")