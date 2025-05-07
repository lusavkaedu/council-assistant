import os
import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime

# === SETTINGS ===
download_base = f"/Users/lgfolder/github/council-assistant/data/council_documents/{topic}"
base_url = "https://democracy.kent.gov.uk/"

mother_urls = [
    "https://democracy.kent.gov.uk/ieListMeetings.aspx?CId=113&Year=0"  # full council
]
topic = "full_council"


# === Unknown date tracker ===
unknown_date_counter = 0
def assign_unknown_folder():
    global unknown_date_counter
    unknown_date_counter += 1
    return f"unknown-{unknown_date_counter}"

# === FUNCTION: Extract meeting date from page ===
def extract_meeting_date(soup):
    text = soup.get_text(" ", strip=True)

    # Pattern 1: "Thursday, 14 September 2023"
    match1 = re.search(
        r"(?:Thursday|Tuesday|Monday|Wednesday|Friday),\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+([A-Za-z]+)(?:,)?\s+(20\d{2})",
        text
    )

    # Pattern 2: "Meeting of County Council held on Thursday, 17 October 2019 at 10.00 am"
    match2 = re.search(
        r"held on (?:Thursday|Tuesday|Monday|Wednesday|Friday),\s+(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})",
        text
    )

    for match in [match1, match2]:
        if match:
            day, month, year = match.groups()
            raw_date = f"{day} {month} {year}"
            try:
                dt = datetime.strptime(raw_date, "%d %B %Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                print(f"  ⚠️ Date parsing error: {raw_date}")

    return None

# === FUNCTION: Categorise document based on filename ===
def get_document_category(filename):
    lower = filename.lower()
    if "agenda" in lower and "front" in lower:
        return "agenda_frontsheet"
    elif "agenda" in lower:
        return "agenda"
    elif "minutes" in lower:
        return "minutes"
    elif "appendix" in lower:
        return "appendix"
    elif "report" in lower:
        return "report"
    elif "questions" in lower:
        return "questions"
    elif "motion" in lower:
        return "motion"
    elif "pack" in lower:
        return "agenda_pack"
    elif "policy" in lower:
        return "policy"
    elif "strategy" in lower:
        return "strategy"
    elif "plan" in lower:
        return "plan"
    elif "budget" in lower:
        return "budget"
    elif "performance" in lower:
        return "performance"
    else:
        return "other"

# === FUNCTION: Download file and collect metadata ===
def download_pdf_and_record_metadata(pdf_url, destination_folder, meeting_date, seen_urls):
    parsed = urlparse(pdf_url)

    # Skip if hostname is missing or clearly internal
    if not parsed.hostname or "kent.gov.uk" not in parsed.hostname:
        print(f"  ⚠️ Skipping invalid or internal link: {pdf_url}")
        return None

    # Skip if URL already processed for this meeting
    if pdf_url in seen_urls:
        print(f"    🔁 Skipping duplicate URL: {pdf_url}")
        return None
    seen_urls.add(pdf_url)

    # Handle duplicate filenames by appending _1, _2, etc.
    filename = os.path.basename(parsed.path)
    original_name = filename
    counter = 1
    while os.path.exists(os.path.join(destination_folder, "originals", filename)):
        filename_parts = os.path.splitext(original_name)
        filename = f"{filename_parts[0]}_{counter}{filename_parts[1]}"
        counter += 1

    path_rel = os.path.join("originals", filename)
    full_path = os.path.join(destination_folder, path_rel)

    # Download file if not already saved
    if not os.path.exists(full_path):
        print(f"    ⬇️ Downloading: {filename}")
        try:
            response = requests.get(pdf_url, timeout=20)
            response.raise_for_status()
        except Exception as e:
            print(f"  ❌ Failed to download {pdf_url}: {e}")
            return None  # Skip this entry on error

        with open(full_path, "wb") as f:
            f.write(response.content)
    else:
        print(f"    ⏩ Skipped (already exists): {filename}")

    # Return metadata
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

# === MAIN SCRAPER LOOP ===
for mother_url in mother_urls:
    print(f"\n🔎 Loading mother page: {mother_url}")
    resp = requests.get(mother_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    child_links = [
        urljoin(base_url, a["href"])
        for a in soup.select("a[href*='ieListDocuments.aspx']")
    ]

    print(f"  ➤ Found {len(child_links)} child pages.")

    for child_url in child_links:
        print(f"\n📄 Scraping child page: {child_url}")
        child_resp = requests.get(child_url)
        child_soup = BeautifulSoup(child_resp.text, "html.parser")

        meeting_date = extract_meeting_date(child_soup)
        if not meeting_date:
            meeting_date = assign_unknown_folder()

        meeting_folder = os.path.join(download_base, meeting_date)
        originals_folder = os.path.join(meeting_folder, "originals")
        os.makedirs(originals_folder, exist_ok=True)

        metadata = []
        seen_urls = set()  # Track URLs to avoid duplicates

        for a in child_soup.select("a[href]"):
            href = a['href']
            if '.pdf' in href.lower():
                pdf_url = urljoin(base_url, href)
                meta_entry = download_pdf_and_record_metadata(
                    pdf_url, meeting_folder, meeting_date, seen_urls
                )
                if meta_entry:
                    metadata.append(meta_entry)

        # === GRANDCHILD LINKS ===
        grandchild_links = [
            urljoin(base_url, a["href"])
            for a in child_soup.select("a")
            if "View the full list of documents" in a.get_text()
        ]

        for g_url in grandchild_links:
            print(f"    ↪️ Scraping grandchild: {g_url}")
            g_resp = requests.get(g_url)
            g_soup = BeautifulSoup(g_resp.text, "html.parser")

            g_date = extract_meeting_date(g_soup) or assign_unknown_folder()
            g_folder = os.path.join(download_base, g_date)
            g_originals = os.path.join(g_folder, "originals")
            os.makedirs(g_originals, exist_ok=True)

            seen_urls = set()  # Reset for each grandchild

            for a in g_soup.select("a[href]"):
                href = a['href']
                if '.pdf' in href.lower():
                    pdf_url = urljoin(base_url, href)
                    meta_entry = download_pdf_and_record_metadata(
                        pdf_url, g_folder, g_date, seen_urls
                    )
                    if meta_entry:
                        metadata.append(meta_entry)

        # === WRITE OR APPEND METADATA FILE (with deduplication) ===
        metadata_path = os.path.join(meeting_folder, "metadata.json")
        
        # Load existing metadata if present
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                existing_metadata = json.load(f)
        except FileNotFoundError:
            existing_metadata = []

        # Remove None entries from new metadata
        metadata = [entry for entry in metadata if entry is not None]

        # Combine and deduplicate by URL
        combined = {entry["url"]: entry for entry in existing_metadata + metadata}
        metadata = list(combined.values())

        # Save updated metadata
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"  🗂️ Metadata updated at {metadata_path}")