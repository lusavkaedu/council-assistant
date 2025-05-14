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
├── README.md                      # This file
```

---

## ✅ Functional Pipeline Summary

### **1. Scraping & Initial Metadata** (`1_scraping_council_docs_DRAFT.py` or notebook)

* Extracts PDF documents from public council pages
* Allocates them into the correct committee/date/originals folder
* Writes basic `metadata.json` per meeting

### **2. Document ID Assignment** (`2_assign_document_ids.py`)

* Assigns unique `doc_id` to each file based on binary content hash
* Detects and removes true duplicates (same binary file) within the same folder
* Updates `document_ids.json` and `document_manifest.jsonl`

### **2b. Text-Based Deduplication** (`2b_text_deduplication.py`)

* Extracts and normalizes text from each PDF
* Computes a SHA256 hash of cleaned text content
* Flags files as `is_text_duplicate_of` in the manifest if their text matches another document
* Prevents re-embedding identical content with different file binaries
* Uses strict equality of SHA256 hashes of normalized text (i.e. 100% content match) — no fuzzy thresholding applied

### **2c. Near-Duplicate Detection** (`2c_near_duplicate_detection.py`)

* Uses MinHash + Locality Sensitive Hashing (LSH) to detect documents with high text similarity
* Applies 5-word shingles and 128 hash permutations
* Flags documents as `is_near_duplicate_of` if their Jaccard similarity ≥ 0.95
* Helps prevent redundant embeddings of semantically similar but not identical files

### **3. Chunking** (`3_chunking_master.py`)

* Processes PDFs into semantic chunks (overlapping if needed)
* Stores `.json` chunk files locally
* Updates manifest with status + chunk path
* Next steps: consider spaCy or NLTK for smarter boundaries, but the regex is clean and efficient for first pass.

### **4. Embeddings** (`4_embedding_master.py`)

* Embeds chunked files using OpenAI models
* Supports both `text-embedding-3-small` and `text-embedding-3-large`
* Writes metadata and builds FAISS index
* Tracks progress in `document_manifest.jsonl`

### **5. Glossary Annotation** (`5_annotate_glossary_links.py`)

* Loads curated glossary terms from `data/glossary/glossary.json`
* Scans all chunked JSON files for mentions of glossary terms or aliases
* Annotates each chunk with a `glossary_terms` field (e.g. `["MRP", "ASC"]`)
* Aggregates glossary tags per document and updates `raw_scraped_metadata.jsonl`
* Enables smarter retrieval, chatbot explanations, and UI tooltips based on term recognition
* Includes a `DRY_RUN = True` mode for safe preview before writing changes
* Next steps needed: improving matching logic (e.g. stemming, plural-insensitive, fuzzy matches)

---

## 🧠 RAG-Ready Metadata Design

* Each document has a `doc_id`, relative path, and hash
* Each chunk has its `chunk_id`, `doc_id`, text, and source
* Manifest file includes status flags:

  * `ready_for_chunking`
  * `chunked`
  * `ready_for_embedding`
  * `embedded`
  * `embedding_large` (optional field)
  * `duplicate_removed` (optional)

---

## 🚧 Next Steps

* [ ] Build notebook-based chatbot using FAISS + OpenAI completion
* [ ] Test retrieval quality using both embedding models
* [ ] Add user history, session memory, or user-level auth (future app layer)


## How the initial data was generated - 

#### Documents
* Council documents: scraped using a notebook code (no script yet, only draft).

#### Other: 
* Civil servants: found a pdf on the council website, with all the names of level 1-3 civil servants and who they report to. Asked ChatGPT to convert it into a a JSONL file. Imported that into people.jsonl.
* Elections: scraped it in the council websites, from 2009 onwards. That added people as candidates/councillors. 
* Committees: copies information on ALL available committees from the Kent County website. https://democracy.kent.gov.uk:9071/ieDocHome.aspx?XXR=0&Year=-1&Page=1&Categories=-14759&EB=F&.  Sent this to Chat GPT to generating starting committees.jsonl. 
