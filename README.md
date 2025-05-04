# Council Assistant

This project enables users (e.g. councillors, researchers, the public) to interact with local government documents through a conversational AI interface. It processes, structures, and indexes council PDFs to support future integration with retrieval-augmented generation (RAG) systems.

---

## 📁 Project Folder Structure

```
council-assistant/
├── data/
│   └── council_documents/
│       ├── committees/
│       │   └── <committee_id>/
│       │       └── <subcommittee_or_category>/
│       │           └── YYYY-MM-DD/                  # Each meeting
│       │               ├── originals/               # Original PDFs
│       │               ├── metadata.json            # Metadata per meeting
│       │               └── *_chunks.json            # Cleaned and chunked text
│       ├── full_council/
│       └── cabinet/
│
├── scripts/
│   ├── process_all.py                # Runs full pipeline
│   ├── delete_all_chunks.py          # Wipe chunk files
│   ├── retro_sort_existing_files.py  # Sort legacy unsorted files
│   ├── generate_all_metadata.py      # Create metadata.json files
│   └── infer_dates_from_text.py      # Pull missing dates from first-page text
│
├── app/
│   ├── __init__.py
│   └── utils/
│       ├── processor.py              # Full PDF → chunks pipeline
│       ├── date_extractor.py         # Date inference from text and filename
│       ├── text_extractor.py         # PDF page-level text extraction
│       └── file_walker.py            # Recursively find valid PDFs
│
└── notebooks/                        # For prototyping and demos
```

---


## ✅ Features Implemented

- 🔍 **PDF Date Detection**: Extracts meeting dates from PDF first pages using regex patterns
- 📂 **Auto-Renaming & Sorting**: Renames and relocates PDFs to dated meeting folders based on extracted or embedded date
- 📄 **Text Extraction**: Uses `pdfplumber` to extract and clean text from PDFs
- ✂️ **Chunking**: Splits clean text into fixed-length chunks for downstream embedding
- 📦 **Chunk Storage**: Saves text chunks as JSON next to their source documents (`*_chunks.json`)
- 🧾 **Metadata Indexing**: (In progress) Generates `metadata.json` in each meeting folder
- 🗃️ **Hybrid Document Handling**:
  - Narrative and scanned PDFs processed into chunks
  - Financial / tabular documents preserved in `tables/` subfolders for custom handling

---

## 🛠 Useful Scripts

| Script                          | Purpose                                        |
|--------------------------------|------------------------------------------------|
| `rename_and_chunk.py`          | Clean, chunk and save text from PDFs          |
| `retro_sort_existing_files.py` | Moves files into proper `YYYY-MM-DD` folders  |
| `scan_unsorted_for_dates.py`   | Logs first-page date matches for untagged PDFs |
| `generate_metadata.py`         | (Planned) Create `metadata.json` for each meeting |

---
## 🛠️ Current Status

- ✅ Folder and data model finalized
- ✅ PDF renaming, chunking, and date inference working
- ✅ Metadata system in place
- ✅ Scripts modular and reusable
- ⏳ Next step: build vector store and frontend chat interface

---

## 🚀 Next Steps

- Vector database + embedding generator
- Streamlit frontend for end-user questions
- Option to filter by committee/date/topic

---

## 🧠 Tech Stack
- Python 3.10+
- pdfplumber
- PyPDF2
- Streamlit (planned)
- OpenAI API (planned for GPT-4 Turbo)
- FAISS or Qdrant (for vector indexing)

---

## Author

Built by [Lucie G] — Kent-based councillor and political technologist.