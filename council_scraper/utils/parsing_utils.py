# parsing_utils.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import re
import time
import random
import http.cookiejar

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
