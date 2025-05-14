#!/bin/bash

cd /Users/lgfolder/github/council-assistant

# Add a date header to the log
echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> log/kent_scraper.log

# Run the scraper and append its output
/Users/lgfolder/opt/anaconda3/envs/myenv/bin/python scripts/kent_news_scraper_rotating.py >> log/kent_scraper.log 2>&1

echo "" >> log/kent_scraper.log  # Add a blank line after each run
