#!/usr/bin/env python3
# main_scraper.py
import os
import argparse
from datetime import datetime

# Import all the utility functions
from utils.scraper_utils_all import (
    run_scrape_batch,
    BASE_URL,
)

#from utils.scraping_utils import run_scrape_batch, BASE_URL

OUTPUT_FILE = "../data/meetings/meetings_metadata_test_1.jsonl"
COMMITTEE_ID = "144"
MIDS_START = 6370
MIDS_END = 9800

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scrape Kent Council meeting data with improved anti-blocking measures")
    parser.add_argument("--output", "-o", default=OUTPUT_FILE, help="Output JSONL file path")
    parser.add_argument("--committee", "-c", default=COMMITTEE_ID, help="Committee ID to scrape")
    parser.add_argument("--start", "-s", type=int, default=MIDS_START, help="Start meeting ID")
    parser.add_argument("--end", "-e", type=int, default=MIDS_END, help="End meeting ID")
    parser.add_argument("--batch-size", "-b", type=int, default=15, help="Max items per session")
    parser.add_argument("--min-cooldown", type=int, default=60, help="Minimum cooldown between sessions (seconds)")
    parser.add_argument("--max-cooldown", type=int, default=180, help="Maximum cooldown between sessions (seconds)")
    parser.add_argument("--weekday-only", action="store_true", help="Only run on weekdays")
    parser.add_argument("--business-hours", action="store_true", help="Only run during business hours (9am-5pm)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    # Check if we should run based on time restrictions
    now = datetime.now()
    is_weekend = now.weekday() >= 5  # 5=Saturday, 6=Sunday
    is_business_hours = 9 <= now.hour < 17
    
    if args.weekday_only and is_weekend:
        print("⏸️ Not running on weekends due to --weekday-only flag")
        exit(0)
        
    if args.business_hours and not is_business_hours:
        print("⏸️ Not running outside business hours due to --business-hours flag")
        exit(0)
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    print(f"🌐 Starting scraper for {BASE_URL}")
    print(f"📁 Output file: {args.output}")
    print(f"🔢 Scraping meeting IDs {args.start} to {args.end}")
    
    # Run the scraper
    mids_range = range(args.start, args.end + 1)
    run_scrape_batch(
        mids=mids_range,
        cid=args.committee,
        output_path=args.output,
        max_per_session=args.batch_size,
        session_cooldown=(args.min_cooldown, args.max_cooldown)
    )
