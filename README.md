# 📘 Council Assistant – Project Overview

Council Assistant is a local-government-focused document intelligence platform that helps councillors, journalists, and citizens search, summarise, and interact with council meeting records. It transforms scattered agendas, minutes, and reports into structured, searchable knowledge — using a metadata-indexed RAG pipeline built on OpenAI embeddings and a meeting-centric file organisation. Initial rollout will be tested with five newly elected councillors from Kent County Council.

## 🚀 GitHub links

https://github.com/lusavkaedu/council-assistant

# Council Assistant - MVP Search Platform

## 🚀 Production Release v1.0

**Kent County Council Records Search** - An AI-powered semantic search platform providing instant access to 12+ years of council records.

### **📊 Platform Scale**
- **2,084 council meetings** spanning 2013-2025
- **14,064 official documents** with AI-generated summaries
- **27,000+ searchable content chunks** in FAISS vector indexes

### **🔍 Core Features**

#### **Intelligent Search**
- **Semantic search** using OpenAI embeddings - find content by meaning, not just keywords
- **Dual search modes**: Meeting discussions (agenda items) and official documents (PDFs)
- **Smart date filtering** with flexible range selection
- **Committee-based filtering** for targeted results

#### **User Experience**
- **Clean, intuitive interface** with prominent search functionality
- **Star-based relevance ratings** (1-5 stars) for result quality
- **Clickable meeting links** to original Kent County Council records
- **Pagination** for efficient browsing of large result sets
- **Mobile-responsive design** for accessibility on all devices

#### **AI-Powered Analysis**
- **Intelligent summarization** of complex policy topics
- **Cross-document insights** analyzing up to 10 most relevant sources
- **Policy trend identification** across multiple meetings and documents
- **Contextual understanding** of local government decisions

### **🎯 Key Capabilities**

**Search Examples:**
- *"SEND schools special educational needs"* → Find discussions about special education provision
- *"road closures traffic management"* → Locate transport planning decisions  
- *"climate change carbon reduction"* → Discover environmental policy developments
- *"housing development planning applications"* → Track planning and development decisions

**Result Quality:**
- **High precision** semantic matching reduces irrelevant results
- **Comprehensive coverage** across all council committees and time periods
- **Professional formatting** with proper text cleaning and structure preservation
- **Direct links** to official Kent County Council meeting pages

### **⚡ Performance**
- **Sub-2 second search** response times for most queries
- **200 result evaluation** before filtering and ranking
- **Real-time date filtering** without index rebuilding
- **Concurrent user support** with session-based state management

### **📈 Production Features**
- **User feedback system** with thumbs up/down quick ratings
- **Comprehensive logging** for usage analytics and optimization
- **Error handling** with graceful degradation
- **Admin dashboard** for real-time monitoring and insights

### **🏛️ Impact**
Democratizes access to local government information, enabling Kent County Council staff and citizens to quickly find relevant decisions, policy developments, and meeting discussions across 12+ years of official records.



## 🛣️ Roadmap (as of 28 May 2025)

- ✅ Scraped all past meetings from council website, together with the pdf links and pdf text (no copies of pdfs are kept, only full text)
- ✅ All the meetings split into agenda items, cleaned and embedded.
- ✅ The scraped pdf links - organised, first 800 words summarised and keywords generated with openAI.
- ✅ PDF (summary+keywords+ title) combo have been embedded.
- ✅ Agenda item and PDF summaries semantic search is working in Streamlit, although the UI needs imrovement
- ✅ All easily available previous elections in Kent have been scraped. Cleaning and metadata separation started, needs to be fininshed. 
- ✅ Councillors profiles scraping module has been developed. Needs to be integrated withthe election data into "Who Is Who" module.
- ✅ Streamlit search page is finalised and published as an MVP.
- 🔜 Build a Who is Who page for streamlit app, allowing councillors to quickly learn about each other. 
- 🔜 Migrate scripts and notebooks and files need to be organsied into a new folder structure
- 🔜 Build a Meeting Prep page for streamlit app, allowing councillors to prepare for upcoming committee meetings.
- 🔜 Build a Committee page for streamlit app, allowing users to access past meetings, future meetings agenda, view profiles of the current members, etc.
- 🔜 Extract metadata and entities from all historical council PDFs using NLP. Various document types require slighly different extraction strategies.  WIP.
- 🔜 Embed full text of the scraped council PDFs - not only summaries. Various document types require slighly different chunking strategies.  WIP. 
- 🔜 Integrate hybrid keyword + semantic search. For now it is only semantic search. 
- 🔜 Build a Planning Applications module, allowing users to monitor past and current planning applications by geographic area
- 🔜 Enable councillor alerts and saved search queries

## 📂 Updated Project Structure (as of 28 May 2025)

```
council-assistant/

├── streamlit_app.py                # 🚀 PRODUCTION: Main search interface (MVP v1.0)
├── pages/                          # Streamlit multi-page application (currently empty, but many in wip)
│   └── archive
│   └── wip
│
├── modules/                        # Core application modules (NEW - production ready), will eventually move pdf_processor, elections, scraper to the modules 
│   ├── data/
│   │   └── loaders.py              # Data loading and validation utilities
│   ├── search/
│   │   ├── semantic_search.py      # FAISS-based semantic search engine
│   │   ├── result_formatters.py    # HTML formatting for search results display
│   │   └── ai_analysis.py          # OpenAI-powered document analysis and summarization
│   └── utils/
│       ├── logging_system.py       # Comprehensive user interaction and performance logging
│       └── feedback_system.py      # User feedback collection and bug reporting interface
│
├── logs/                           # 🆕 Production logging (auto-created)
│   ├── search_queries.jsonl        # User search patterns and performance metrics
│   ├── user_feedback.jsonl         # User ratings and feedback submissions
│   ├── user_interactions.jsonl     # Tab usage, filter preferences, navigation
│   ├── errors.jsonl                # Application errors and debugging info
│   ├── performance.jsonl           # System performance and response times
│   └── application.log             # General application logging
│
├── admin_dashboard.py              # 🆕 PRODUCTION: Standalone admin analytics dashboard
├── streamlit_app.py                # 🆕 Main application entry point, currently has only one page. 
│
├── data/                           # Production data pipeline
│   ├── metadata/                   # 🆕 Consolidated metadata (PRODUCTION READY)
│   │   ├── meetings.jsonl          # Meeting metadata with web codes and dates
│   │   ├── agendas.jsonl           # Agenda items with cleaned text
│   │   └── pdf_warehouse.jsonl     # Document metadata with display titles and URLs
│   │
│   ├── embeddings/                 # FAISS indexes + embedding metadata (PRODUCTION)
│   │   ├── agendas/
│   │   │   ├── agenda_index.faiss         # Semantic search index for agenda items
│   │   │   └── metadata_agenda.jsonl      # Agenda embedding metadata
│   │   └── pdf_summaries/
│   │       ├── pdf_summary_index.faiss    # Semantic search index for document summaries
│   │       └── metadata_pdf_summaries.jsonl # PDF embedding metadata
│   │
│   ├── pdf_full_text/              # Extracted PDF text files
│   │   ├── kcc_cc_2016-06-22_d5312b.txt
│   │   └── [14,000+ additional .txt files]
│   │
│   ├── pdf_metadata/               # PDF extraction metadata
│   │   └── scraped_pdf_metadata.jsonl
│   │
│   └── processed_register/         # Processing pipeline tracking
│       ├── document_ids.json       # Document ID mappings
│       ├── pdf_manifest.jsonl      # PDF processing status tracking
│       ├── pdf_manifest_backup.jsonl
│       └── agenda_manifest.jsonl   # Agenda processing status tracking
│
├── council_scraper/                # Data collection pipeline
│   ├── main_scraper.py            # Entry point for scraping council websites
│   └── utils/                     # HTTP, parsing, and scraping utilities
│       ├── __init__.py
│       ├── http_utils.py
│       ├── parsing_utils.py
│       └── scraping_utils.py
│
├── pdf_processor/                  # Document processing pipeline
│   ├── claude_scraping_script.py         # Main PDF bulk scraping script
│   ├── claude_summarization_script.py    # PDF summarization pipeline
│   ├── reset_errors_to_pending.py        # Manifest reset utility
│   └── utils/                             # PDF processing utilities
│
├── prompts/                        # AI prompt templates
│   ├── mom_summarisation_v1.prompt       # Meeting minutes summarization
│   └── planning_summarisation.prompt     # Planning document summarization
│
├── archive/                        # Legacy code and deprecated scripts
├── elections/                      # Election-related data (future development)
├── notebooks/                      # Data analysis and development notebooks
├── scripts/                        # Processing pipeline scripts
├── app/                           # Reserved for future chatbot development
│   ├── embeddings/                # Future chatbot logic
│   └── utils/                     # Reserved utilities
│
├── .env                           # Environment variables (OpenAI API keys)
└── README.md                      # Project documentation
```

## 🚀 Production Status

### **LIVE & PRODUCTION READY:**
- **`streamlit_app.py`** - Main search interface serving Kent County Council
- **`modules/`** - Complete modular architecture with search, formatting, and analytics
- **`admin_dashboard.py`** - Real-time usage analytics and system monitoring
- **`data/metadata/`** - Clean, validated data powering the search experience
- **`data/embeddings/`** - Semantic search indexes with 27K+ document chunks
- **`logs/`** - Comprehensive user analytics and feedback collection

### **DEVELOPMENT/PIPELINE:**
- **`council_scraper/`** - Data collection from Kent County Council websites
- **`pdf_processor/`** - Document processing and AI summarization pipeline
- **`prompts/`** - AI prompt optimization for better summarization

### **ARCHIVED/LEGACY:**
- **`archive/`** - Deprecated scripts and old implementations
- **`logic/`** - MOVED to `modules/search/` for production
- **Legacy FAISS files** - Replaced by organized embeddings structure

## 📊 Scale & Performance

**Production Data (as of May 2025):**
- **2,084 council meetings** (2013-2025)
- **14,064 official documents** with AI summaries
- **27,000+ searchable content chunks** in dual FAISS indexes
- **Sub-2 second search** response times
- **Real-time analytics** and user feedback collection

## 🛠️ Key Improvements Made

1. **Modular Architecture** - Clean separation of concerns in `modules/`
2. **Production Logging** - Comprehensive analytics in `logs/`
3. **Admin Dashboard** - Standalone monitoring interface
4. **Data Consolidation** - Cleaned metadata in `data/metadata/`
5. **User Experience** - Professional search interface with feedback systems
6. **Error Handling** - Robust exception handling and graceful degradation


## Target folder structure (need to migrate towards it)

council-assistant/
├── app.py                      # Main Streamlit entry point
├── requirements.txt            # Dependencies for your app
├── README.md
│
├── pages/                      # Streamlit pages (your current structure)
│   ├── Search_Council_Records.py
│   ├── Who_Is_Who.py
│   ├── Committee_Browser.py
│   └── Ask_GPT.py
│
├── modules/                    # Your core application logic
│   ├── scraping/              # council_scraper → here
│   │   ├── __init__.py
│   │   ├── main_scraper.py
│   │   └── utils/
│   ├── processing/            # pdf_processor → here  
│   │   ├── __init__.py
│   │   ├── pdf_scraper.py
│   │   ├── summarization.py
│   │   └── utils/
│   ├── search/               # logic → here
│   │   ├── __init__.py
│   │   ├── semantic_search.py
│   │   ├── load_data.py
│   │   └── formatting.py
│   ├── people/               # New organized people module
│   │   ├── __init__.py
│   │   ├── matching.py
│   │   └── cleaning.py
│   └── utils/                # utils → here
│       ├── __init__.py
│       ├── documents.py
│       └── elections_helpers/
│
├── scripts/                   # Data processing scripts (run separately)
│   ├── pipeline/             # Core data processing pipeline
│   │   ├── 01_scrape_meetings.py
│   │   ├── 02_clean_meetings.py
│   │   ├── 03_process_pdfs.py
│   │   ├── 04_embed_content.py
│   │   └── 05_build_indexes.py
│   ├── maintenance/          # Utility/maintenance scripts
│   │   ├── reset_manifests.py
│   │   ├── rebuild_indexes.py
│   │   └── validate_data.py
│   └── experimental/         # Draft/test scripts
│
├── notebooks/                # Analysis notebooks
│   ├── active/              # Currently used notebooks
│   ├── archive/             # Old/completed notebooks
│   └── scratch/             # Quick experiments
│
└── data/                    # data files

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

## ✅ A. Functional Pipeline Summary FOR Agenda Items (Web-Scraped)

### 🕸️ Scraper Module Overview (`council_scraper/`)

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


#### 📊 Notebook: 0D_Scraping_EDA_Agenda_Meetings_Metadata.ipynb

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


#### 🧾 Script: `scripts/0a_generate_committee_summary.py`

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


#### 🧹 Script `scripts/0b_scraped_meetings_cleaner.py`

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

#### 🧹 Script `scripts/2_prepare_agenda_manifest.py`

To support high-quality agenda embedding, notebook named "EDA_agenda_items_detailed_analysis.ipynb" was used to develop and test filtering rules that exclude low-value items (e.g., procedural, redacted, or webcast-only). The process is now codified in the script [`scripts/2_prepare_agenda_manifest.py`], which applies refined logic for `junk_flag` and `embed_status` based on word count, category, and name cues. Approximately **70%** of agenda items were excluded as non-informative, resulting in a reduced and high-signal manifest of **7,198** items saved to [`data/processed_register/agenda_manifest.jsonl`](data/processed_register/agenda_manifest.jsonl). ~70% of items were filtered out and 7,198 retained. 

#### 🧠 Script `scripts/4_embedding_master_agendas.py`

This script embeds high-quality agenda items into a FAISS index using OpenAI’s embedding API. It reads from `agenda_manifest.jsonl`, filters out already embedded items, and processes the remaining entries in batches.

- **Combines `item_title` and `item_text`** to form a semantic unit for each chunk
- **Embeds using `text-embedding-3-small`**, storing vectors in `agendas/agenda_index.faiss`
- **Logs metadata to `agendas/metadata_agenda.jsonl`**, preserving chunk and meeting context
- **Updates manifest** to flag each item as `embedding_small = true` once completed

Run this script after finalising the manifest, and before enabling semantic search in the Streamlit app.

### 🔧 TODO – Embedding Pipeline Enhancements

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


## B.  Documents/PDFs processing track:


#### 📄 `pdf_processor/claude_scraping_script.py`

This script scrapes council PDFs, extracts full text and metadata, and saves them in a unified structure for downstream processing.
It verifies whether each PDF has already been scraped (via `.txt` presence or manifest) and skips duplicates.
Extracted data includes text, PDF metadata (author, creator, dates), and number of tables detected.
Instead of saving individual JSON files, it appends one line per document to a central JSONL file: `scraped_pdf_metadata.jsonl`.
A manifest (`pdf_manifest.jsonl`) tracks scraping status (`scraped: true/false`) and allows safe resumption after interruption.


#### 📊 `notebooks/Dashboard.ipynb`

This notebook provides a real-time overview of the scraping pipeline.
It summarizes progress using `pdf_manifest.jsonl`, tracking documents marked as scraped, summarised, chunked, and embedded.
It also analyzes extracted PDF metadata from `scraped_pdf_metadata.jsonl`, showing common tools, missing fields, and creation timelines.
Visual timelines display scraping activity down to the minute, helping debug stalls or monitor ingestion bursts.
Designed for interactive use in Jupyter or Streamlit, it supports quick diagnostics and pipeline auditing.


#### 📊 # pdf_processor/claude_summarization_script.py
<!-- 🔄 one by one GPT Summarisation  -->

- Summarisation now runs via a fault-tolerant batch script using OpenAI GPT. 1 by 1, not in batches. 
- Automatically skips already processed documents and EQIA-type files.
- Summaries and keywords are appended to a unified `summaries.jsonl` file.
- Manifest is updated live with status, timestamp, and error messages.


### 🧠 Open AI Batch Summarisation Workflow

#### pdf_processor/submit_batch_job.py

Prepares a batch of documents (up to 3500) for OpenAI Batch API processing.
It selects the most recent documents with full text and metadata, builds prompts, and writes the request file to batch_requests.jsonl.
Also updates the pdf_manifest.jsonl to flag selected documents as batch_status: "pending".

#### pdf_processor/upload_batch_to_openai.py

Uploads the batch request file to OpenAI’s Batch API.
Handles file creation and job submission, returning a batch ID for monitoring.
Must be run once batch_requests.jsonl is ready and OPENAI_API_KEY is set.

#### pdf_processor/process_batch_results.py

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


## Who is Who Module

data/people
├── raw_sources/                    # Unmodified scraped or imported files
│   ├── whocanivotefor/            
│   │   └── kent_candidate_profiles.jsonl
│   ├── kcc_tv/
│   │   └── kcc_councillors_scrape_2025-05-25.json
│   ├── election_results/
│   │   └── kent_2025_local_election_results.csv
│   └── ... (other named sources)
│
├── cleaned_people/                # Harmonised person records (deduplicated, clean names, stable IDs)
│   └── people_warehouse.jsonl        # Each person gets a canonical ID and merged fields, canonical person with metadata
│
├── reference/              # Helper lookup tables
│   ├── aliases.json               # Maps known name variants to canonical form, flat lookup used during cleaning/matching
│   ├── councils.json              # Canonical list of councils
│   ├── parties.json               # Party standardisation mapping
│   └── ...
│
├── intermediate/                  # Join tables, matches, flags
│   ├── matched_candidates_to_councillors.csv
│   ├── unresolved_duplicates.csv
│   └── ...
│
└── logs/                          # Logs from matching and cleaning runs
    └── name_cleaning_run_2025-05-25.json


## Utilities

utils/
├── __init__.py
├── documents.py
├── elections_cleaning_helpers
│   ├── __init__.py
│   ├── matching_helpers.py
│   ├── party_cleaning.py
│   └── ward_cleaning.py


## App  - Search Page support module 
Created modules/search subfolder. It hold everything related to teh search page of the app"

# Council Assistant - Modules Overview

## 📁 Modules Structure

The `modules/` folder contains the core functionality of the Council Assistant, organized into logical components for maintainability and scalability.

```
modules/
├── data/
│   └── loaders.py                 # Data loading and validation utilities
├── search/
│   ├── semantic_search.py         # FAISS-based semantic search engine
│   ├── result_formatters.py       # HTML formatting for search results display
│   └── ai_analysis.py            # OpenAI-powered document analysis and summarization
└── utils/
    ├── logging_system.py         # Comprehensive user interaction and performance logging
    └── feedback_system.py        # User feedback collection and bug reporting interface
```

## 📋 Module Descriptions

### **Data Management (`data/`)**
- **`loaders.py`** - Loads and validates JSONL data files (meetings, agendas, documents), performs integrity checks

### **Search Functionality (`search/`)**
- **`semantic_search.py`** - Core search engine using FAISS indexes and OpenAI embeddings for semantic document retrieval
- **`result_formatters.py`** - Formats search results into user-friendly HTML tables with clickable links, star ratings, and pagination
- **`ai_analysis.py`** - Generates intelligent summaries and policy analysis using OpenAI GPT models on search results

### **System Utilities (`utils/`)**
- **`logging_system.py`** - Tracks user searches, performance metrics, errors, and interactions for analytics and monitoring
- **`feedback_system.py`** - Collects user feedback, bug reports, and satisfaction ratings through interactive UI components

## 🔧 Key Features

### **Semantic Search Engine**
- **FAISS vector search** across 27K+ document chunks
- **Dual indexes** for agenda items and PDF document summaries  
- **Relevance scoring** with 1-5 star visual ratings
- **Committee and date filtering** for refined results

### **AI-Powered Analysis**
- **Document summarization** using GPT-4 models
- **Policy trend analysis** across multiple sources
- **Contextual insights** from up to 10 most relevant sources (4 agenda items + 6 documents)

### **User Experience**
- **Clean HTML formatting** with clickable meeting links
- **Pagination support** for large result sets
- **Real-time feedback collection** with thumbs up/down quick ratings
- **Comprehensive error handling** and user guidance

### **Admin Analytics**
- **Search pattern tracking** - popular queries, success rates, performance metrics
- **User behavior analysis** - tab usage, filter preferences, session patterns  
- **System health monitoring** - error rates, response times, data quality
- **Feedback aggregation** - user satisfaction trends and feature requests

## 📊 Data Flow

1. **User Query** → `semantic_search.py` → FAISS vector similarity search
2. **Raw Results** → `result_formatters.py` → Formatted HTML with links and ratings
3. **User Interactions** → `logging_system.py` → Analytics database
4. **AI Analysis Request** → `ai_analysis.py` → GPT-powered insights
5. **User Feedback** → `feedback_system.py` → Feedback database

## 🛠️ Technical Stack

- **Vector Search**: FAISS indexes with OpenAI text-embedding-3-small
- **Data Storage**: JSONL files for metadata, separate FAISS indexes for embeddings
- **AI Processing**: OpenAI GPT-4o-mini for analysis and summarization
- **Frontend**: Streamlit with custom HTML/CSS formatting
- **Analytics**: JSON Lines logging with Pandas analysis
- **Deployment**: Local/cloud Streamlit deployment with admin dashboard

## 📈 Scalability

The modular architecture allows for easy extension:
- **New search indexes** can be added to `semantic_search.py`
- **Additional formatters** can extend `result_formatters.py` 
- **Enhanced analytics** can build on `logging_system.py`
- **AI capabilities** can be expanded in `ai_analysis.py`