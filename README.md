# 📘 Council Assistant – Project Overview

The **Council Assistant** is a local-government-focused document intelligence platform designed to assist teams in searching, summarising, and interacting with meeting documents such as agendas, minutes, appendices, reports, and motions. It uses a metadata-indexed RAG pipeline, built on OpenAI embeddings, and is structured around a meeting-centric file organisation.

---

## 📂 Current Project Structure (as of May 2025)

```
council-assistant/
├── app/
│   ├── embeddings/                  # Future home for production app logic (chatbot)
│   └── utils/                       # Reserved for helper functions (currently empty)
│
├── archive/                         # Archived legacy scripts or versions no longer in use
│
├── data/
│   ├── council_documents/                    # Meeting-centric raw documents (PDFs)
│   │   ├── cabinet/                          # Top-level committee folder
│   │   │   ├── 2025-01-30/                   # Meeting date
│   │   │   │   ├── originals/                # Original scraped PDFs
│   │   │   │   ├── chunks/                   # Chunked JSON files (optional, future)
│   │   │   │   └── metadata.json             # Metadata describing documents in this meeting
│   │   ├── full_council/
│   │   │   ├── 2025-03-13/
│   │   │   │   ├── originals/
│   │   │   │   ├── chunks/
│   │   │   │   └── metadata.json
│   │   └── duplicates/                       # Duplicate PDFs safely moved here during de-duplication
│   │
│   ├── glossary/                      # Curated term definitions used for enrichment
│   │   └── glossary.json              # Canonical glossary entries with term metadata
│   │
│   ├── embeddings/                 # FAISS indexes + embedding metadata
│   │   ├── council_index.faiss
│   │   ├── council_index_large.faiss
│   │   ├── metadata.jsonl
│   │   └── metadata_large.jsonl
│   │
│   ├── processed_register/        # Canonical metadata tracking
│   │   ├── document_ids.json      # Mapping: relative file path → doc_id + content hash
│   │   └── document_manifest.jsonl # Status tracking: chunked / embedded / duplicated / removed
│
├── notebooks/
│   ├── 1_Scraping_council_docs_KCC.ipynb      # Main scraping notebook
│   └── 2_Duplicate_hashes.ipynb               # Notebook for auditing and reviewing duplicates
│
├── scripts/                        # Finalised script pipeline (chronologically ordered)
│   ├── 1_scraping_council_docs_DRAFT.py       # Main scraper + initial metadata writer
│   ├── 2_assign_document_ids.py               # Assigns doc_ids + hashes + deduplicates
│   ├── 3_chunking_master.py                   # Context-aware chunking pipeline
│   └── 4_embedding_master.py                  # Embedding with OpenAI, both small & large models
│
├── council_scraper/                 # Dedicated module for scraping and parsing raw council data
│   ├── main_scraper.py              # Entry point for scraping council websites
│   └── utils/                       # Helper functions for HTTP, parsing, and scraping logic
│       ├── __init__.py
│       ├── http_utils.py
│       ├── parsing_utils.py
│       └── scraping_utils.py
├── README.md                      # This file
```

---

## ✅ Functional Pipeline Summary — Agenda Items (Web-Scraped)


### 🧹 Prep step - set up committees - Committee List Cleaner (Manual Setup for New Councils)
`notebooks/0A_Scraping_KCC_Committees.ipynb`

This notebook extracts and cleans committee names from a saved HTML file of the council’s meeting index page.  
It tags inactive bodies, removes irrelevant entries, and builds a canonical alias map.  
Run this manually when onboarding a **new council** to ensure accurate committee matching.  
Outputs include `committees.jsonl` and `committee_alias_map.csv` for use in downstream processing.


### **0. Scrape Meetings from Website** (`0_scrape_meetings.py`)

* Scrapes meeting metadata and agenda items from `https://democracy.kent.gov.uk`
* Supports scraping any `COMMITTEE_ID` and range of `MId` values
* Detects meeting status (e.g. `cancelled`, `moved`, `withdrawn`)
* Extracts structured fields: `committee_name`, `meeting_date`, `agenda_items`, and linked PDF URLs
* Appends results to `data/meetings/kcc_meetings.jsonl`
* Assigns each meeting a stable `meeting_id = "{COUNCIL_CODE}_{web_meeting_code}"`

#### 🧼 `meeting_cleaning.py` — Agenda Data Cleaner + Committee Metadata Generator

This utility script prepares council meeting data for use across the platform by cleaning agenda items, standardizing metadata, and producing a reusable committee reference file.

- Normalizes committee names using alias rules and canonical names
- Filters out junk/procedural agenda items (e.g. apologies, declarations)
- Cleans agenda item titles (e.g. strips "PDF 123 KB")
- Standardizes date formats for consistency
- Drops meetings with no meaningful content

🔁 Also generates `data/metadata/committees.jsonl`:
- Canonical name + all observed aliases
- Assigns a short, unique `committee_id` for use across the pipeline
- Tagged with `council_code = "kent_cc"`

Used in downstream workflows: agenda chunking, embedding, search, glossary tagging, and UI filters.

---

The two scripts above have been integrated now into this:

## 🕸️ Scraper Module Overview (`council_scraper/`)

This module contains all scripts and utilities used to scrape public meeting data from local government council websites.

### 📁 Folder Structure
council_scraper/
├── main_scraper.py           # CLI entry point to run the scraper
└── utils/
  ├── init.py           # Exports shared utility functions
  ├── http_utils.py         # HTTP request wrappers with retry logic and headers
  ├── parsing_utils.py      # Text/date cleaning, regex helpers, structural parsers
  └── scraping_utils.py     # Core scraping logic: page navigation, metadata extraction, file writing

### 🧠 Design Principles
- Modular: each helper script is self-contained and reusable
- Resilient: request functions include error handling and backoff logic
- Clean output: all scraped data is saved as `.jsonl` and includes status metadata
- Scalable: scraper can be adapted to support multiple councils or extended to fetch PDFs

### ✅ Usage
Run the scraper from the project root:
```bash
python3 council_scraper/main_scraper.py --start 6000 --end 9800 --committee 144 --output data/meetings/kcc_meetings.jsonl

data/meetings/kcc_meetings.jsonl = the main source of information later used for agenda.jsonl, meetings.jsonl, etc. 



## 📊 Notebook: 0D_Scraping_EDA_Agenda_Meetings_Metadata.ipynb

This notebook performs **exploratory data analysis (EDA)** and **initial cleaning** on the raw scraped metadata from council meeting agenda pages. It serves as the first diagnostic step in the pipeline, helping to validate the structure and quality of the scraped data before downstream processing.

#### Key Tasks:
- Loads and previews raw `kcc_meetings.jsonl` content
- Identifies and removes duplicate or malformed entries
- Explores distribution of scraped agenda items by:
  - Committee
  - Meeting date
  - Agenda category
- Highlights issues in `item_text`, such as empty rows, overlong junk content, or missing PDFs
- Flags potential inconsistencies for manual or rule-based cleaning
- Prepares cleaned metadata for downstream enrichment (e.g., categorisation, filtering, embedding)

Use this notebook to iteratively improve scraping logic and ensure the dataset remains accurate and complete across councils and time periods.


### 🧾 Script: `1_generate_committee_summary.py`

This script generates a clean, merged summary of all committees based on scraped meeting metadata. It performs the following key tasks:

- Loads and deduplicates raw meeting records from `kcc_meetings.jsonl`
- Cleans and normalises committee names (e.g. removes suffixes like ", Budget Meeting")
- Aggregates meeting stats (first/last date, count) for each unique committee
- Merges with the legacy committee metadata (`starter_list_committees.jsonl`)
- Auto-classifies committees as `inactive` if no meetings in 3+ years
- Filters out inactive committees with fewer than 2 meetings
- Outputs the final summary to `committees.jsonl`

**When to run:**  
Run this script after scraping new meeting data but **before indexing documents or building committee dashboards**. It ensures your committee list stays up-to-date and consistent across the project.


### 🧹 `0_scraped_meetings_cleaner.py`

This script processes raw meeting metadata scraped from the council website. It splits the raw scraped data into distinct parts by sperforms the following:

- **Cleans and deduplicates** meeting entries.
- **Normalizes committee names** and assigns `committee_id` by matching against `committees.jsonl`.
- **Flattens agenda items** and sub-items into a single agenda row per PDF reference.
- **Identifies and logs unassigned PDFs**, then creates fallback agenda items to preserve them.
- **Links documents to agenda items**, assigns `doc_id`s, and deduplicates all PDF references.
- Outputs three final datasets:
  - `meetings.jsonl` — cleaned meetings with assigned committee IDs
  - `agendas.jsonl` — flattened and enriched agenda items
  - `documents.jsonl` — deduplicated PDF metadata with `doc_id`, `agenda_id`, and `meeting_id`

Use this script after scraping, and **after cleaning committees names to canonical ones**, and before embedding or summarisation.








### **1. Generate Agenda Chunks** (`1_generate_agenda_chunks.py`)

* Processes all entries in `kcc_meetings.jsonl`
* Extracts and flattens agenda items into chunks
* Computes a stable `chunk_id` based on meeting ID and item number
* Adds a `text_hash` (SHA256) to each chunk for content tracking
* Filters out empty or irrelevant agenda items (e.g. titles only, no text)
* Saves full set of raw agenda chunks to `data/chunks/minutes/chunks.jsonl`

---

### **2. Update Manifest for Embedding** (`2_update_manifest.py`)

* Compares newly generated chunks to existing `document_manifest.jsonl`
* Flags new or changed chunks as `ready_for_embedding`
* Assigns `doc_id = "webscrape_<date>_<meeting_code>"` to each chunk
* Updates or inserts manifest entries for agenda-derived chunks
* Ensures previously embedded chunks are not reprocessed if unchanged

---

### **3. Embed Agenda Chunks** (`4_embedding_master.py`)

* Reads manifest and embeds only those agenda chunks marked `ready_for_embedding`
* Skips chunks with `embedding_small = true` and identical `text_hash`
* Sends batches to OpenAI embedding API (using `text-embedding-3-small` or other model)
* Stores embedded vectors and metadata to:
  - `data/embeddings/agenda/metadata.jsonl`
  - `data/embeddings/agenda/index.faiss`
* Updates manifest to flag each chunk as embedded


## DOCUMENTS PDF processing

1_scrape_docs.py     → just saves PDFs + metadata

2_classify_docs.py   → tags type: "minutes", "agenda", "report", etc

3_process_minutes.py → special handler for minutes
3_process_decision.py → special handler for minutes
3_process_prod.py → special handler for minutes
3_process_eqia.py → special handler for minutes
3_process_planning_app.py → special handler for minutes



4_embed_chunks.py    → generic embedding

