# utils/__init__.py
# This file makes the utils directory a proper Python package

BASE_URL = "https://democracy.kent.gov.uk"

# You can expose the main functions here to simplify imports
from .http_utils import get_random_headers, create_session, request_with_retry #done
from .parsing_utils import clean_day_suffix, load_seen_ids, generate_pdf_attachment_check  #done
from .scraping_utils import scrape_meeting_metadata, run_scrape_batch #done
