import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import re
import time
import random
import hashlib
from pathlib import Path
from tqdm import tqdm

BASE_URL = "https://democracy.kent.gov.uk"
COMMITTEE_ID = "144"
COUNCIL_CODE = "kent_cc"
MIDS = range(5959, 5960)  # Change as needed
OUTPUT_FILE = "data/meetings/meetings_metadata.jsonl"

# Paths for chunk output
CHUNK_OUTPUT_FOLDER = Path("data/chunks/minutes/")
CHUNK_OUTPUT_PATH = CHUNK_OUTPUT_FOLDER / "chunks.jsonl"
CHUNK_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Keywords to filter out low-value items
LOW_SIGNAL_KEYWORDS = [
    "apologies", "substitutes", "panel business",
    "motion to exclude", "minutes of the meeting",
    "future work programme", "webcast", "any other business"
]

def clean_day_suffix(date_str):
    return re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', date_str)

def load_seen_ids(output_file):
    seen = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    seen.add(obj["web_meeting_code"])
                except:
                    continue
    return seen

def scrape_meeting_metadata(mid, cid="144"):
    url = f"{BASE_URL}/ieListDocuments.aspx?CId={cid}&MId={mid}"

    try:
        res = requests.get(url, timeout=6)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")

        # --- Status detection ---
        page_title = soup.find("title").text.strip()
        status_match = re.search(r'\b(CANCELLED|WITHDRAWN|POSTPONED|MOVED|NEW)\b', page_title.upper())
        status = status_match.group(1).lower() if status_match else "scheduled"

        # --- Heading and metadata ---
        title_candidates = soup.find_all(["h1", "h2"])
        full_heading = ""
        for tag in title_candidates:
            if "Committee" in tag.get_text() or re.search(r"\d{4}", tag.get_text()):
                full_heading = tag.get_text(strip=True)
                break

        match = re.match(
            r"^(.*?)\s*-\s*(Monday|Tuesday|Wednesday|Thursday|Friday),\s*(.*?),\s*(\d{4})\s*(\d{1,2}\.\d{2})\s*(am|pm)",
            full_heading
        )

        if match:
            committee_name = match.group(1).strip()
            raw_day = clean_day_suffix(match.group(3))
            meeting_date = datetime.strptime(f"{raw_day}, {match.group(4)}", "%d %B, %Y").strftime("%Y-%m-%d")
            meeting_time = datetime.strptime(match.group(5) + match.group(6), "%I.%M%p").strftime("%H:%M")
        else:
            committee_name = None
            meeting_date = None
            meeting_time = None

        # --- Agenda item extraction with PDFs ---
        agenda_items = []
        for row in soup.find_all("tr"):
            number_cell = row.find("td", class_="mgItemNumberCell")
            content_cells = row.find_all("td")
            if number_cell and len(content_cells) > 1:
                item_number = number_cell.get_text(strip=True)
                content_td = content_cells[1]
                paragraphs = content_td.find_all("p")
                item_title = paragraphs[0].get_text(strip=True) if paragraphs else ""
                item_text = "\n".join(p.get_text(strip=True) for p in paragraphs[1:]) if len(paragraphs) > 1 else ""

                # Find any PDF links inside this agenda item
                item_pdfs = []
                for a in content_td.find_all("a", href=True):
                    href = a["href"]
                    if href.lower().endswith(".pdf"):
                        full_url = BASE_URL + "/" + href.lstrip("/")
                        item_pdfs.append(full_url)

                agenda_items.append({
                    "item_number": item_number,
                    "item_title": item_title,
                    "item_text": item_text,
                    "pdf_urls": item_pdfs
                })

        return {
            "web_meeting_code": str(mid),
            "meeting_title": full_heading,
            "meeting_status": status,
            "committee_name": committee_name,
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "agenda_items": agenda_items
        }

    except Exception as e:
        return {"web_meeting_code": str(mid), "error": str(e)}

def run_scrape_batch(mids, cid, output_path, delay=(1.5, 3.5)):
    seen_ids = load_seen_ids(output_path)
    with open(output_path, "a", encoding="utf-8") as f:
        for mid in tqdm(mids, desc="Scraping meetings"):
            if str(mid) in seen_ids:
                continue
            data = scrape_meeting_metadata(mid, cid)
            if data:
                data["meeting_id"] = f"{COUNCIL_CODE}_{data['web_meeting_code']}"
                data["scrape_timestamp"] = datetime.now().isoformat()
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            time.sleep(random.uniform(*delay))

if __name__ == "__main__":
    run_scrape_batch(MIDS, COMMITTEE_ID, OUTPUT_FILE)