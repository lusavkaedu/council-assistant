# 🏛️ Council Assistant

**Council Assistant** is a professional-grade Streamlit-based web app for searching and summarising local government documents. It uses OpenAI embeddings and a meeting-centric file structure to make committee reports, agendas, and minutes searchable, contextual, and linkable.

---

## ✅ Project Status

| Feature                            | Status       |
|-----------------------------------|--------------|
| PDF scraping & metadata generation | ✅ Complete  |
| Text cleaning & chunking pipeline | ✅ With LlamaIndex (semantic) |
| Metadata-backed chunking          | ✅ Per-file, with URL support |
| FAISS index building (resumable)  | ✅ Safe & restartable |
| OpenAI embedding generation       | 🟡 In Progress |
| Streamlit interface               | 🟡 MVP started |
| Filtering by committee/date/type | 🔜 Planned   |
| Advanced table handling           | 🔜 Planned   |
| Deployment                        | 🔜 Streamlit sharing / Docker |

---

## 📁 Folder Structure

```plaintext
council-assistant/
├── data/
│   ├── council_documents/
│   │   └── committees/<committee>/<meeting_date>/
│   │       ├── originals/                        # Raw PDFs
│   │       ├── *_chunks.json                     # Cleaned + chunked text
│   │       ├── metadata.json                     # Metadata with URL, type, date
│   └── embeddings/
│       └── council_index.faiss                   # FAISS index
│
├── app/
│   ├── embeddings/
│   │   ├── embedder.py
│   │   ├── index_builder_resumable.py
│   │   └── retriever.py
│   ├── utils/
│   │   ├── cleaner.py
│   │   ├── chunker.py (LlamaIndex splitter)
│   │   ├── file_walker.py
│   │   └── processor.py
│   └── streamlit_app.py                          # (WIP) Streamlit frontend
│
├── scripts/
│   ├── process_all.py                            # Run full pipeline
│   ├── delete_all_chunks.py
│   ├── generate_metadata.py
│   ├── scan_unsorted_for_dates.py
│   └── create_meeting_folders.py
```

---

## 🧠 Technologies

- **OpenAI Embeddings** (e.g. `text-embedding-3-small`)
- **FAISS** for fast vector search
- **LlamaIndex** for semantic-aware text splitting
- **Streamlit** for frontend
- **PDFplumber + custom cleaner** for extraction
- **Metadata.json** links each chunk to its file, type, committee, URL, etc.

---

## 💡 Usage Guide

1. **Scrape & save PDFs**  
   PDFs and metadata are saved under the correct `committees/<date>/originals/` folders automatically.

2. **Run the chunking pipeline**  
   ```bash
   export PYTHONPATH=.
   python scripts/process_all.py
   ```

3. **Generate embeddings (resumable-safe)**  
   ```bash
   export PYTHONPATH=.
   python app/embeddings/index_builder_resumable.py
   ```

4. **Launch Streamlit frontend**  
   *(Once MVP is complete)*  
   ```bash
   streamlit run app/streamlit_app.py
   ```

---

## 🛡️ Robustness Features

- ✅ Skips already chunked files
- ✅ Resumable embedding with checkpointed saving
- ✅ Metadata validation per file
- 🛠️ Ongoing improvements to handle tables, authentication, and caching

---

## 🔜 Roadmap

- [ ] Streamlit interface with document filters
- [ ] Table extraction and CSV export
- [ ] Incremental file watcher (every 15 mins)
- [ ] Query logging and insights
- [ ] Authentication for multi-user deployment

---

## 🤝 License

MIT License – build your own local AI assistant for civic transparency.