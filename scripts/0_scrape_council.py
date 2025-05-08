"""
0_scraping council documents.py

Standalone script to scrape all council PDFs.
Input are from a csv file called committes.csv
"""


import os
import re
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging

logging.basicConfig(
    filename="scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# === LOAD TOPIC + URL PAIRS FROM CSV ===
committee_list = pd.read_csv("/data/scraping_targets/committees.csv")

# Add status column if missing
if 'status' not in committee_list.columns:
    committee_list['status'] = 'not_started'

# === UNKNOWN DATE TRACKER ===
unknown_date_counter = 0
def assign_unknown_folder():
    global unknown_date_counter
    unknown_date_counter += 1
    return f"unknown-{unknown_date_counter}"

def extract_meeting_date(soup):
    text = soup.get_text(" ", strip=True)

    match1 = re.search(
        r"(?:Thursday|Tuesday|Monday|Wednesday|Friday),\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+([A-Za-z]+)(?:,)?\s+(20\d{2})", text
    )
    match2 = re.search(
        r"held on (?:Thursday|Tuesday|Monday|Wednesday|Friday),\s+(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})", text
    )

    for match in [match1, match2]:
        if match:
            day, month, year = match.groups()
            raw_date = f"{day} {month} {year}"
            try:
                dt = datetime.strptime(raw_date, "%d %B %Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                logging.warning(f"  ⚠️ Date parsing error: {raw_date}")

    return None

def get_document_category(filename):
    lower = filename.lower()
    keywords = {
        "agenda_frontsheet": ["agenda", "front"],
        "agenda": ["agenda", "additional agenda", "agenda item"],
        "minutes": ["printed minutes", "cpp minutes", "minutes of previous", "minutes"],
        "questions": ["questions put", "answers to questions", "q&a"],
        "appendix": ["appendix", "annex"],
        "motion": ["motion", "mtld"],
        "amendment": ["amendment"],
        "budget": ["budget", "revenue plan"],
        "report": ["report", "covering report", "update"],
        "decision_response": ["response", "decision", "record of decision"],
        "strategy": ["strategy", "investment strategy", "capital strategy"],
        "plan": ["plan", "local plan", "delivery plan"],
        "policy": ["policy", "statement"],
        "consultation": ["consultation"],
        "performance": ["performance", "quarterly performance", "qpr"],
        "terms_of_reference": ["terms of reference", "tor"],
        "supporting_material": ["glossary", "note", "you said we did"]
    }
    for category, patterns in keywords.items():
        if any(p in lower for p in patterns):
            return category
    return "other"

def download_pdf_and_record_metadata(pdf_url, destination_folder, meeting_date, seen_urls, topic):
    parsed = urlparse(pdf_url)
    if not parsed.hostname or "kent.gov.uk" not in parsed.hostname:
        logging.warning(f"  ⚠️ Skipping invalid or internal link: {pdf_url}")
        return None
    if pdf_url in seen_urls:
        logging.info(f"    🔁 Skipping duplicate URL: {pdf_url}")
        return None
    seen_urls.add(pdf_url)

    filename = os.path.basename(parsed.path)
    original_name = filename
    counter = 1
    while os.path.exists(os.path.join(destination_folder, "originals", filename)):
        name_parts = os.path.splitext(original_name)
        filename = f"{name_parts[0]}_{counter}{name_parts[1]}"
        counter += 1

    path_rel = os.path.join("originals", filename)
    full_path = os.path.join(destination_folder, path_rel)

    if not os.path.exists(full_path):
        logging.info(f"    ⬇️ Downloading: {filename}")
        try:
            response = requests.get(pdf_url, timeout=20)
            response.raise_for_status()
            with open(full_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            logging.warning(f"  ❌ Failed to download {pdf_url}: {e}")
            return None
    else:
        logging.info(f"    ⏩ Skipped (already exists): {filename}")

    return {
        "filename": filename,
        "path": path_rel,
        "type": "pdf",
        "committee": topic,
        "meeting_date": meeting_date,
        "document_category": get_document_category(filename),
        "url": pdf_url,
        "created": datetime.now().isoformat()
    }

# === MAIN SCRIPT LOOP ===
base_url = "https://democracy.kent.gov.uk/"

for _, row in committee_list.iterrows():
    if row['status'] == 'completed':
        continue
    idx = committee_list.index[committee_list['topic'] == row['topic']].tolist()[0]
    committee_list.at[idx, 'status'] = 'in_progress'
    committee_list.to_csv("/data/scraping_targets/committees.csv", index=False)

    topic = row["topic"]
    mother_urls = [row["mother_url"]]
    download_base = f"/Users/lgfolder/Downloads/data scrape full 1 page only/{topic}"

    logging.info(f"\n📂 Starting topic: {topic}")

    for mother_url in mother_urls:
        logging.info(f"\n🔎 Loading mother page: {mother_url}")
        resp = requests.get(mother_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        child_links = [
            urljoin(base_url, a["href"])
            for a in soup.select("a[href*='ieListDocuments.aspx']")
        ]
        logging.info(f"  ➤ Found {len(child_links)} child pages.")

        for child_url in child_links:
            logging.info(f"\n📄 Scraping child page: {child_url}")
            child_resp = requests.get(child_url)
            child_soup = BeautifulSoup(child_resp.text, "html.parser")

            meeting_date = extract_meeting_date(child_soup) or assign_unknown_folder()
            meeting_folder = os.path.join(download_base, meeting_date)
            originals_folder = os.path.join(meeting_folder, "originals")
            os.makedirs(originals_folder, exist_ok=True)

            metadata = []
            seen_urls = set()

            for a in child_soup.select("a[href]"):
                href = a['href']
                if '.pdf' in href.lower():
                    pdf_url = urljoin(base_url, href)
                    meta_entry = download_pdf_and_record_metadata(
                        pdf_url, meeting_folder, meeting_date, seen_urls, topic
                    )
                    if meta_entry:
                        metadata.append(meta_entry)

            grandchild_links = [
                urljoin(base_url, a["href"])
                for a in child_soup.select("a")
                if "View the full list of documents" in a.get_text()
            ]

            for g_url in grandchild_links:
                logging.info(f"    ↪️ Scraping grandchild: {g_url}")
                g_resp = requests.get(g_url)
                g_soup = BeautifulSoup(g_resp.text, "html.parser")

                g_date = extract_meeting_date(g_soup) or assign_unknown_folder()
                g_folder = os.path.join(download_base, g_date)
                g_originals = os.path.join(g_folder, "originals")
                os.makedirs(g_originals, exist_ok=True)

                seen_urls = set()

                for a in g_soup.select("a[href]"):
                    href = a['href']
                    if '.pdf' in href.lower():
                        pdf_url = urljoin(base_url, href)
                        meta_entry = download_pdf_and_record_metadata(
                            pdf_url, g_folder, g_date, seen_urls, topic
                        )
                        if meta_entry:
                            metadata.append(meta_entry)

            metadata_path = os.path.join(meeting_folder, "metadata.json")

            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    existing_metadata = json.load(f)
            except FileNotFoundError:
                existing_metadata = []

            metadata = [m for m in metadata if m is not None]
            combined = {m["url"]: m for m in existing_metadata + metadata}
            metadata = list(combined.values())

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logging.info(f"  🗂️ Metadata updated at {metadata_path}")

    committee_list.at[idx, 'status'] = 'completed'
    committee_list.to_csv("/data/scraping_targets/committees.csv", index=False)