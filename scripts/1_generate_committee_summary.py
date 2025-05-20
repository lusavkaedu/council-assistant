# scripts/1_generate_committee_summary.py

# === IMPORTS ===
import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re
import pandas as pd

# === CONFIGURATION ===
LEGACY_PATH = Path("data/committees/starter_list_committees.jsonl") # this is the starter file formed by scraping the KCC list of committees from the website 
INPUT_PATH = Path("data/meetings/kcc_meetings.jsonl")
OUTPUT_PATH = Path("data/metadata/committees.jsonl")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# === HELPER FUNCTIONS ===
# Helper: slugify committee name into ID
def slugify(name):
    name = name.lower()
    name = name.replace("’", "'")  # smart quotes
    name = re.sub(r"'s\b", "s", name)  # convert possessive to s
    name = re.sub(r"\bcommittee\b", "", name, flags=re.IGNORECASE)  # remove "committee"
    name = re.sub(r"[^\w\s]", "", name)  # remove punctuation
    name = re.sub(r"\s+", "-", name.strip())
    name = re.sub(r"-+", "-", name)  # clean double hyphens
    name = name.strip("-")
    return name

# === STEP 1: Load and clean raw meetings data ===
df = pd.read_json(INPUT_PATH, lines=True)

# Drop duplicates by web_meeting_code, keep the latest
df = df.drop_duplicates(subset='web_meeting_code', keep='last')

# Parse and clean date
df['meeting_date'] = pd.to_datetime(df['meeting_date'], errors='coerce')
df = df.dropna(subset=['meeting_date'])

# Clean and normalize committee names (extract last part after comma)
def extract_last_part(name):
    if pd.isna(name):
        return name
    return name.rsplit(',', 1)[1].strip() if ',' in name else name

df['committee_name'] = df['committee_name'].apply(extract_last_part)

print(f"📥 Loaded {len(df)} total meetings")
print(f"🧾 Found {df['committee_name'].nunique()} unique committee names")

# === STEP 2: Build committee dictionary from cleaned names ===
committees = defaultdict(list)
for _, row in df.iterrows():
    if pd.notna(row["committee_name"]) and pd.notna(row["meeting_date"]):
        cid = slugify(row["committee_name"])
        committees[cid].append({
            "name": row["committee_name"],
            "date": row["meeting_date"].strftime("%Y-%m-%d")
        })

# Insert aggregation info printout
total_committee_records = sum(len(v) for v in committees.values())
print(f"🔗 Before aggregation: {len(committees)} unique committees linked to {total_committee_records} meetings")

# === STEP 3: Aggregate meetings by committee ===
records = []
for cid, meetings in committees.items():
    dates = [m["date"] for m in meetings if m["date"]]
    try:
        first = min(dates)
        last = max(dates)
    except ValueError:
        continue  # skip empty
    records.append({
        "committee_id": cid,
        "committee_name": meetings[0]["name"],
        "first_meeting_date": first,
        "last_meeting_date": last,
        "meeting_count": len(dates)
    })


legacy_data = {}

# === STEP 4: Load and merge legacy committee metadata ===
if LEGACY_PATH.exists():
    with open(LEGACY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if "committee_id" in entry:
                    legacy_data[entry["committee_id"]] = entry
            except:
                continue

# Merge or add computed committee summaries
for r in records:
    cid = r["committee_id"]
    r_name = r["committee_name"]
    matched_id = None

    # Match on canonical_name or aliases
    for legacy_id, legacy_entry in legacy_data.items():
        if r_name == legacy_entry.get("canonical_name"):
            matched_id = legacy_id
            break
        if r_name in legacy_entry.get("aliases", []):
            matched_id = legacy_id
            break

    if matched_id:
        legacy_data[matched_id].update(r)
    else:
        legacy_data[cid] = r


# Replace records list with merged output
records = list(legacy_data.values())

from datetime import timedelta

# === STEP 5: Prune inactive or low-activity committees ===
# Automatically mark stale committees as inactive
today = datetime.today()
for r in records:
    try:
        last_meeting = datetime.strptime(r["last_meeting_date"], "%Y-%m-%d")
        if (today - last_meeting).days > 730:  # 2 years
            r["status"] = "inactive"
    except:
        continue

# Filter out inactive committees with fewer than 2 meetings
records = [
    r for r in records
    if not (r.get("status", "active") != "active" and r.get("meeting_count", 0) < 1)
]

num_active = sum(1 for r in records if r.get("status", "active") == "active")
num_inactive = sum(1 for r in records if r.get("status", "active") != "active")
print(f"📊 Final committee summary: {num_active} active, {num_inactive} inactive")

# === STEP 6: Save final committee summary ===
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for r in sorted(records, key=lambda x: x["committee_id"]):
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"✅ Saved {len(records)} committees to {OUTPUT_PATH}")