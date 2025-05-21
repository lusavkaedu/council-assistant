# 📘 Council Assistant – Project Overview

Council Assistant is a local-government-focused document intelligence platform that helps councillors, journalists, and citizens search, summarise, and interact with council meeting records. It transforms scattered agendas, minutes, and reports into structured, searchable knowledge — using a metadata-indexed RAG pipeline built on OpenAI embeddings and a meeting-centric file organisation. Initial rollout is tested with five newly elected councillors from Kent County Council.

## 🚀 Quick Start

1. Clone the repository  
   ```bash
   git clone https://github.com/YOUR-REPO-HERE
   cd council-assistant
   ```

2. Install dependencies  
   *(Create a `requirements.txt` manually if needed)*  
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app  
   ```bash
   streamlit run streamlit_app.py
   ```

4. Set environment variables  
   - You will need an OpenAI API key: `OPENAI_API_KEY=your-key-here`

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
├── council_scraper/                 # Dedicated module for scraping and parsing raw council data
│   ├── main_scraper.py              # Entry point for scraping council websites
│   └── utils/                       # Helper functions for HTTP, parsing, and scraping logic
│       ├── __init__.py
│       ├── http_utils.py
│       ├── parsing_utils.py
│       └── scraping_utils.py
│
├── data/│   
│   ├── glossary/                      # Curated term definitions used for enrichment
│   │   └── glossary.json              # Canonical glossary entries with term metadata
│   │  
│   ├── chunks/                        # Future place for chunks
│   │   └── agenda_chunks.jsonl        # not yet ready
│   │   ├── pdf_chunks.jsonl            # not yet ready
│   │
│   ├── embeddings/                  # FAISS indexes + embedding metadata
│   │   ├── council_index_small.faiss   # legacy files, need to be regenerated separatelt for pdfs and agendas 
│   │   ├── council_index_large.faiss
│   │   ├── metadata_small.jsonl
│   │   └── metadata_large.jsonl
│   │
│   ├── pdf_full_text/            # several thousands of .txt files with text of the scraped pdfs.
│   │   ├── kcc_cc_2016-06-22_d5312b.txt 
│   │   ├── etc
│   │
│   ├── pdf_metadata/       
│   │   ├── scraped_pdf_metadata.jsonl   # pdf metadata extracted during scraping: d
│   │
│   ├── processed_register/        # Metadata tracking
│   │   ├── document_ids.json              # Mapping: doc_id + pdf_url
│   │   ├── pdf_manifest.jsonl             # Main manifest for PDF documents (scraped, summarised, embedded, etc)
│   │   ├── pdf_manifest_backup.jsonl      # Backup of the PDF manifest
│   │   ├── agenda_manifest.jsonl          # Manifest tracking agenda item chunks (chunked, embedded, etc)
│   │   └── document_manifest.jsonl        # Legacy, no longer used
│
├── elections/   
│
├── pdf_processor/
│   └── 4_summarise_AI_pdfs_archived.py   # Legacy Script 
│   └── reset_errors_to_pending.py   # script to reset the document manifest - be careful using it.   
│   └── claude_scraping_script.py    # the main pdf bulk scraping script  
│   └── claude_summarization_script.py   # to be developed
│
for downloading pdfs text, saving it, categorising it, sending for summarisation and keywords extraction
│   └── utils/                                 # Helper functions for processing pdfs
│
├── prompts/
│   ├──prompts/mom_summarisation_v1.prompt
│   └──prompts/planning_summarisation.prompt 
│
├── notebooks/
│   ├── 
│   └── 
│
├── scripts/                        # Finalised script pipeline 
│   ├── 
│   ├── 
│   ├── 
│   └── 
│
├── README.md                      # This file
```


### 🧱 Architectural Note: Separate Manifests for Agendas and PDFs

To simplify maintenance and improve clarity, we have split the manifest files into two separate sources:

- `pdf_manifest.jsonl` tracks the ingestion status of **full PDF documents**, including scrape, summarisation, and embedding stages.
- `agenda_manifest.jsonl` independently tracks **web-scraped agenda item chunks**, including chunking, hashing, and embedding.

This avoids overloading a single manifest file and makes it easier to debug or update one pipeline without affecting the other. Each manifest is tightly scoped to its document type but shares a compatible schema (e.g. `doc_id`, `chunk_id`, `text_hash`, `embedding_small`) to support unified embedding and search later on.



## 🔄 Data & Pipeline Flow

```
[Raw HTML for meetings]
    ↓
[Scraper] → [Full Organised Text + PDF Urls + Metadata]
    ↓
[Cleaning] → [metadata jsonl for meetings, agendas, committees, documents/pdfs]
    ↓
[LLMs via API] → [Add GPT summaries + keywords to document metadata]
    ↓
[Chunker + Embedder] → [FAISS + Manifest]
    ↓
[Streamlit App] → [Semantic Search | Councillor Tools | Meeting Browser | Who's Who Profiles]
```

- Full PDF documents are not saved — only extracted text is stored in `data/pdf_full_text/`
- Summaries (in pilot) are saved to the metadata files

---

## 🧠 App Features Overview

- 🔍 **Agenda Search** — Semantic search among past meeting agenda items
- 🧑‍💼 **Who’s Who** — Profiles of councillors, officers, and election candidates
- 🏛️ **Meeting View** — View all agenda items for a selected meeting
- 📅 **Committee View** — Browse all past meetings and upcoming agendas
- 🤖 **Ask GPT** — Developer panel for testing summarisation and hybrid search

---

## ✅ Functional Pipeline Summary — Agenda Items (Web-Scraped)

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


### 🧾 Script: `scripts/0a_generate_committee_summary.py`

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


### 🧹 Script `scripts/0b_scraped_meetings_cleaner.py`

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

### 🧹 Script `scripts/2_prepare_agenda_manifest.py`

To support high-quality agenda embedding, notebook named "EDA_agenda_items_detailed_analysis.ipynb" was used to develop and test filtering rules that exclude low-value items (e.g., procedural, redacted, or webcast-only). The process is now codified in the script [`scripts/2_prepare_agenda_manifest.py`], which applies refined logic for `junk_flag` and `embed_status` based on word count, category, and name cues. Approximately **70%** of agenda items were excluded as non-informative, resulting in a reduced and high-signal manifest of **7,198** items saved to [`data/processed_register/agenda_manifest.jsonl`](data/processed_register/agenda_manifest.jsonl). ~70% of items were filtered out and 7,198 retained. 

### 🧠 Script `scripts/4_embedding_master_agendas.py`

This script embeds high-quality agenda items into a FAISS index using OpenAI’s embedding API. It reads from `agenda_manifest.jsonl`, filters out already embedded items, and processes the remaining entries in batches.

- **Combines `item_title` and `item_text`** to form a semantic unit for each chunk
- **Embeds using `text-embedding-3-small`**, storing vectors in `agenda_index.faiss`
- **Logs metadata to `metadata_agenda.jsonl`**, preserving chunk and meeting context
- **Updates manifest** to flag each item as `embedding_small = true` once completed

Run this script after finalising the manifest, and before enabling semantic search in the Streamlit app.

## 🔧 TODO – Embedding Pipeline Enhancements

- [ ] **Add manifest auto-backup**  
  Before overwriting `agenda_manifest.jsonl`, write a dated copy to `agenda_manifest_backup_YYYYMMDD.jsonl`.

- [ ] **Implement `--dry-run` mode in embedding script**  
  Allow previewing which agenda chunks would be embedded, without making changes.

- [ ] **Log embedded chunks to append-only log**  
  Write each successfully embedded record to `embedding_log_agenda.jsonl` with timestamp and chunk ID.

- [ ] **Add versioned FAISS index output**  
  Save `agenda_index_<YYYYMMDD>.faiss` alongside latest file to retain historical snapshots.

- [ ] **Gracefully skip already embedded records**  
  Allow re-running the embedding script without any risk of duplication or overwrite.

- [ ] **Visual dashboard to monitor embedding progress**  
  Show counts of total agenda items, embedded, skipped, and errored — for peace of mind.


## Documents/PDFs processing track:


### 📄 `pdf_processor/claude_scraping_script.py`

This script scrapes council PDFs, extracts full text and metadata, and saves them in a unified structure for downstream processing.
It verifies whether each PDF has already been scraped (via `.txt` presence or manifest) and skips duplicates.
Extracted data includes text, PDF metadata (author, creator, dates), and number of tables detected.
Instead of saving individual JSON files, it appends one line per document to a central JSONL file: `scraped_pdf_metadata.jsonl`.
A manifest (`pdf_manifest.jsonl`) tracks scraping status (`scraped: true/false`) and allows safe resumption after interruption.


### 📊 `notebooks/Dashboard.ipynb`

This notebook provides a real-time overview of the scraping pipeline.
It summarizes progress using `pdf_manifest.jsonl`, tracking documents marked as scraped, summarised, chunked, and embedded.
It also analyzes extracted PDF metadata from `scraped_pdf_metadata.jsonl`, showing common tools, missing fields, and creation timelines.
Visual timelines display scraping activity down to the minute, helping debug stalls or monitor ingestion bursts.
Designed for interactive use in Jupyter or Streamlit, it supports quick diagnostics and pipeline auditing.


### 📊 # pdf_processor/claude_summarization_script.py
<!-- 🔄 one by one GPT Summarisation  -->

- Summarisation now runs via a fault-tolerant batch script using OpenAI GPT. 1 by 1, not in batches. 
- Automatically skips already processed documents and EQIA-type files.
- Summaries and keywords are appended to a unified `summaries.jsonl` file.
- Manifest is updated live with status, timestamp, and error messages.


### 🧠 Open AI Batch Summarisation Workflow

pdf_processor/submit_batch_job.py

Prepares a batch of documents (up to 3500) for OpenAI Batch API processing.
It selects the most recent documents with full text and metadata, builds prompts, and writes the request file to batch_requests.jsonl.
Also updates the pdf_manifest.jsonl to flag selected documents as batch_status: "pending".

pdf_processor/upload_batch_to_openai.py

Uploads the batch request file to OpenAI’s Batch API.
Handles file creation and job submission, returning a batch ID for monitoring.
Must be run once batch_requests.jsonl is ready and OPENAI_API_KEY is set.

pdf_processor/process_batch_results.py

Processes the results returned by OpenAI’s Batch API (from batch_results.jsonl).
It extracts summary info (title, summary, keywords), appends to summaries.jsonl, updates the manifest, and generates semantic embeddings using text-embedding-3-small.
Embeddings are saved in pdf_summary_embeddings.jsonl.

      📂 Source Metadata + Text
      ┌───────────────┬──────────────┬──────────────┐
      │ documents.jsonl │ scraped_pdf_metadata.jsonl │ pdf_full_text/ │
      └───────────────┴──────────────┴──────────────┘
                   │
                   ▼
         🧠 submit_batch_job.py
   [merge metadata + build GPT prompts]
                   │
                   ▼
     📝 batch_requests.jsonl   ←─── updates manifest (batch_status: pending)
                   │
                   ▼
         🚀 upload_batch_to_openai.py
         [sends batch → OpenAI API]
                   │
           [wait for 24h batch processing]
                   ▼
       📥 batch_results.jsonl (downloaded)
                   │
                   ▼
     🧠 process_batch_results.py
     ├── writes summaries → summaries.jsonl
     ├── writes embeddings → pdf_summary_embeddings.jsonl
     └── updates manifest (batch_status: complete, summarised: true)



### PLAN:


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

---

## 🛣️ Roadmap (as of May 2025)

- ✅ Core committee and meeting dashboard live
- ✅ Agenda item semantic search working
- 🔜 Embed all historical council PDFs
- 🔜 Add GPT-based summaries and keyword extractions
- 🔜 Integrate hybrid keyword + semantic search
- 🔜 Enable councillor alerts and saved search queries
