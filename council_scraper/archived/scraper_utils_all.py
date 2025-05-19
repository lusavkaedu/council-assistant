# scraper_utils.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import re
import time
import random
import http.cookiejar

BASE_URL = "https://democracy.kent.gov.uk"

def get_random_headers():
    """Generate random-looking but realistic browser headers"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    
    # Common accept headers
    accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    accept_language = "en-GB,en;q=0.9"
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": accept,
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }
    
    # Occasionally add a referer to make it seem like we clicked a link
    if random.random() > 0.7:
        headers["Referer"] = "https://democracy.kent.gov.uk/ieDocHome.aspx"
        
    return headers

def create_session():
    """Create a persistent session object with cookies enabled"""
    session = requests.Session()
    # Set a cookie policy that accepts all cookies
    session.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(
        allowed_domains=None,  # Allow all domains
    ))
    return session

def request_with_retry(session, url, max_retries=3, backoff_factor=1.5):
    """Make a request with exponential backoff retry logic"""
    headers = get_random_headers()
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Vary the timeout slightly
            timeout = random.uniform(8, 12)
            response = session.get(url, headers=headers, timeout=timeout)
            
            # If successful, return the response
            if response.status_code == 200:
                return response
                
            # If we get a 403 or 429, back off and retry
            if response.status_code in (403, 429):
                retry_count += 1
                wait_time = backoff_factor ** retry_count
                # Add some randomness to the wait time
                wait_time = wait_time * random.uniform(0.8, 1.2)
                print(f"⚠️ Got status {response.status_code}, waiting {wait_time:.2f}s before retry {retry_count}/{max_retries}")
                time.sleep(wait_time)
                continue
                
            # For other status codes, just return the response
            return response
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            retry_count += 1
            wait_time = backoff_factor ** retry_count
            print(f"⚠️ Connection error: {str(e)}, waiting {wait_time:.2f}s before retry {retry_count}/{max_retries}")
            time.sleep(wait_time)
    
    # If we've exhausted all retries, raise an exception
    raise Exception(f"Failed to retrieve {url} after {max_retries} retries")

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

def generate_pdf_attachment_check(meeting):
    attached = set()
    
    for item in meeting.get("agenda_items", []):
        for url in item.get("pdf_urls", []):
            attached.add(url)
        for sub in item.get("sub_items", []):
            for url in sub.get("pdf_urls", []):
                attached.add(url)

    header_pdfs = set(meeting.get("header_pdf_urls", []))
    all_pdfs = attached.union(header_pdfs)

    meeting["attached_pdfs"] = len(attached)
    meeting["header_pdfs"] = len(header_pdfs)
    meeting["total_pdfs_found"] = len(all_pdfs)
    meeting["pdfs_unassigned"] = len(header_pdfs)
    meeting["pdf_attachment_ok"] = len(header_pdfs) == 0

    return meeting

def scrape_meeting_metadata(mid, cid="144", session=None):
    """
    Scrape metadata for a specific meeting
    
    Args:
        mid: Meeting ID
        cid: Committee ID
        session: Requests session (optional)
    """
    url = f"{BASE_URL}/ieListDocuments.aspx?CId={cid}&MId={mid}"
    timestamp = datetime.utcnow().isoformat()
    
    # Use provided session or create a new one
    use_session = session if session else requests.Session()

    try:
        # Use our retry-enabled request function
        if session:
            res = request_with_retry(use_session, url)
        else:
            # Fall back to simple request if no session provided
            res = use_session.get(url, headers=get_random_headers(), timeout=10)
            
        if res.status_code != 200:
            return {
                "web_meeting_code": str(mid),
                "meeting_id": f"kent_cc_{mid}",
                "scrape_timestamp": timestamp,
                "error": f"Status code {res.status_code}"
            }

        soup = BeautifulSoup(res.text, "html.parser")
        
        # Detect if we've been blocked
        if "access denied" in soup.get_text().lower() or "forbidden" in soup.get_text().lower():
            return {
                "web_meeting_code": str(mid),
                "meeting_id": f"kent_cc_{mid}",
                "scrape_timestamp": timestamp,
                "error": "Access denied - likely rate limited"
            }

        # --- Detect meeting status ---
        page_title = soup.find("title").text.strip()
        status_match = re.search(r'\b(CANCELLED|WITHDRAWN|POSTPONED|MOVED|NEW)\b', page_title.upper())
        status = status_match.group(1).lower() if status_match else "scheduled"

        # --- Extract meeting heading and time ---
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

        # --- Gather all PDFs on the page ---
        all_pdfs = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                full_url = BASE_URL + "/" + href.lstrip("/")
                all_pdfs.add(full_url)

        # --- Agenda item parsing ---
        agenda_items = []
        used_pdfs = set()
        agenda_table = soup.find("table", class_="mgItemTable")

        if agenda_table:
            for row in agenda_table.find_all("tr"):
                number_cell = row.find("td", class_="mgItemNumberCell")
                content_cells = row.find_all("td")

                if number_cell and len(content_cells) > 1:
                    item_number = number_cell.get_text(strip=True).rstrip('.')
                    content_td = content_cells[1]

                    item_title = content_td.find("p", class_="mgAiTitleTxt")
                    item_title = item_title.get_text(strip=True) if item_title else ""

                    item_data = {
                        "item_number": item_number,
                        "item_title": item_title,
                        "sub_items": [],
                        "pdf_urls": []
                    }

                    sub_items = content_td.find_all(["p", "ul", "div"], class_=["mgSubItemTitleTxt", "mgBulletList", "mgWordPara"])
                    current_sub_item = None

                    for element in sub_items:
                        if 'mgSubItemTitleTxt' in element.get('class', []):
                            if current_sub_item:
                                item_data["sub_items"].append(current_sub_item)
                            current_sub_item = {
                                "title": element.get_text(strip=True),
                                "content": "",
                                "pdf_urls": []
                            }
                        elif current_sub_item:
                            if element.name == "ul":
                                current_sub_item["content"] += "\n".join([li.get_text(strip=True) for li in element.find_all("li")])
                            else:
                                current_sub_item["content"] += element.get_text(strip=True) + "\n"
                            for a in element.find_all("a", href=True):
                                href = a["href"]
                                if href.lower().endswith(".pdf"):
                                    full_url = BASE_URL + "/" + href.lstrip("/")
                                    current_sub_item["pdf_urls"].append(full_url)
                                    item_data["pdf_urls"].append(full_url)
                                    used_pdfs.add(full_url)

                    if current_sub_item:
                        item_data["sub_items"].append(current_sub_item)

                    # 🩹 Patch: also scan the entire content_td for orphaned PDF links
                    for a in content_td.find_all("a", href=True):
                        href = a["href"]
                        if href.lower().endswith(".pdf"):
                            full_url = BASE_URL + "/" + href.lstrip("/")
                            if full_url not in item_data["pdf_urls"]:
                                item_data["pdf_urls"].append(full_url)
                                used_pdfs.add(full_url)

                    # If no sub-items, fallback to full block text
                    if not item_data["sub_items"]:
                        item_data["content"] = content_td.get_text(" ", strip=True)

                    agenda_items.append(item_data)

        # --- Remaining header-level PDFs ---
        header_pdf_urls = sorted(all_pdfs - used_pdfs)

        return {
            "web_meeting_code": str(mid),
            "meeting_id": f"kent_cc_{mid}",
            "scrape_timestamp": timestamp,
            "error": None,
            "meeting_title": full_heading,
            "meeting_status": status,
            "committee_name": committee_name,
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "agenda_items": agenda_items,
            "header_pdf_urls": header_pdf_urls
        }

    except Exception as e:
        return {
            "web_meeting_code": str(mid),
            "meeting_id": f"kent_cc_{mid}",
            "scrape_timestamp": timestamp,
            "error": str(e)
        }
    finally:
        # Close the session if we created it here
        if not session:
            use_session.close()

def run_scrape_batch(mids, cid, output_path, max_per_session=15, session_cooldown=(60, 180)):
    """
    Scrape in small batches with natural pauses and session rotation
    
    Args:
        mids: Meeting IDs to scrape
        cid: Committee ID
        output_path: Where to save results
        max_per_session: Maximum requests per session before rotating
        session_cooldown: Tuple of (min, max) seconds to wait between sessions
    """
    # Load previously scraped meeting codes
    seen_ids = load_seen_ids(output_path)
    mids_to_scrape = [mid for mid in mids if str(mid) not in seen_ids]
    
    if not mids_to_scrape:
        print("✅ All meetings already scraped!")
        return
        
    print(f"🔍 Found {len(mids_to_scrape)} meetings to scrape")
    
    # Split into smaller batches
    remaining = len(mids_to_scrape)
    session_count = 0
    
    with open(output_path, "a", encoding="utf-8") as f:
        while remaining > 0:
            session_count += 1
            print(f"📌 Starting session #{session_count}")
            
            # Create a fresh session
            session = create_session()
            
            # Decide how many items to process in this session (variable)
            items_this_session = min(remaining, random.randint(max(1, max_per_session-5), max_per_session))
            
            # Get the next batch of meeting IDs
            batch = mids_to_scrape[:items_this_session]
            mids_to_scrape = mids_to_scrape[items_this_session:]
            remaining -= items_this_session
            
            # Process this batch
            for idx, mid in enumerate(batch):
                print(f"  [{idx+1}/{items_this_session}] Processing meeting {mid}")
                
                try:
                    # First, visit the committee page - just like a human would
                    if idx == 0:
                        committee_url = f"{BASE_URL}/mgCommitteeDetails.aspx?ID={cid}"
                        print(f"    👆 Visiting committee page first")
                        committee_response = request_with_retry(session, committee_url)
                        # Brief pause after visiting the committee page
                        time.sleep(random.uniform(1.5, 3.0))
                    
                    # Now scrape the actual meeting
                    data = scrape_meeting_metadata(mid, cid, session)
                    
                    # Add QA metadata if scrape was successful
                    if data and not data.get("error"):
                        data = generate_pdf_attachment_check(data)
                        if not data.get("pdf_attachment_ok", True):
                            print(f"    ⚠️ {data['meeting_id']}: {data['pdfs_unassigned']} unassigned PDFs")
                    
                    # Write all scraped results (good or error)
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    
                except Exception as e:
                    print(f"    ❌ Error scraping meeting {mid}: {str(e)}")
                    # Write error record
                    error_data = {
                        "web_meeting_code": str(mid),
                        "meeting_id": f"kent_cc_{mid}",
                        "scrape_timestamp": datetime.utcnow().isoformat(),
                        "error": str(e)
                    }
                    f.write(json.dumps(error_data, ensure_ascii=False) + "\n")
                
                # Variable delay between requests - more human-like
                if idx < len(batch) - 1:  # No need to wait after the last item
                    # Occasionally have a longer pause as if the user got distracted
                    if random.random() < 0.1:  # 10% chance of a "distraction"
                        pause = random.uniform(8, 15)
                        print(f"    ⏸️ Taking a longer break ({pause:.1f}s)")
                    else:
                        pause = random.uniform(3, 7)
                        print(f"    ⏳ Waiting {pause:.1f}s")
                    time.sleep(pause)
            
            # After finishing a session, take a longer break before the next one
            if remaining > 0:
                cooldown = random.uniform(*session_cooldown)
                print(f"🛌 Session #{session_count} complete. Taking a break for {cooldown:.1f}s before next session")
                print(f"📊 Progress: {len(mids) - remaining}/{len(mids)} meetings processed ({remaining} remaining)")
                time.sleep(cooldown)
                
    print(f"✅ Scrape complete. Processed {len(mids) - len(seen_ids)} meetings.")
