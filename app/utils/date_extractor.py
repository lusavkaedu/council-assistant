# ✅ Final `date_extractor.py`
# Central utility for extracting structured dates from filenames or text

import re

month_map = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

# Regex patterns to try in order
pattern_full = re.compile(r"(\d{1,2})[-\s](January|February|March|April|May|June|July|August|September|October|November|December)[-\s](\d{4})", re.IGNORECASE)
pattern_month_year = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s\-](\d{4})", re.IGNORECASE)
pattern_numeric = re.compile(r"(\d{2})(\d{2})(\d{4})(?:\s(\d{4}))?")
filename_pattern = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?")


def extract_date_from_text(text):
    for pattern in [pattern_full, pattern_month_year]:
        match = pattern.search(text)
        if match:
            try:
                if pattern == pattern_full:
                    day, month_name, year = match.groups()
                    return f"{year}-{month_map[month_name.lower()]}-{day.zfill(2)}"
                else:
                    month_name, year = match.groups()
                    return f"{year}-{month_map[month_name.lower()]}"
            except Exception:
                continue
    return None


def extract_date_from_filename(filename):
    match = filename_pattern.match(filename)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}" if day else f"{year}-{month}"
    return "Unknown"
