# app/streamlit_app.py

import streamlit as st
import uuid
from datetime import datetime
from pathlib import Path

# --- Simple access control ---
def check_password():
    st.sidebar.title("Login")
    password = st.sidebar.text_input("Enter password", type="password")
    if password != st.secrets.get("app_password", ""):
        st.warning("Access denied.")
        st.stop()

check_password()
import json
import openai
import faiss
import numpy as np
import os
import pandas as pd

DEBUG = False  # Set True to display raw prompt/context info

# --- Load environment ---
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

def log_query(query_text, page="Ask GPT"):
    log_path = Path("log/query_log.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": st.session_state["session_id"],
        "page": page,
        "query": query_text
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# --- Load metadata and FAISS index ---
@st.cache_resource
def load_data():
    import jsonlines
    from pathlib import Path

    metadata_path = Path("data/embeddings/metadata_large.jsonl")
    with jsonlines.open(metadata_path, "r") as reader:
        records = list(reader)
    metadata_df = pd.DataFrame(records)

    doc_meta_path = Path("data/document_metadata/raw_scraped_metadata.jsonl")
    doc_meta_lookup = {}
    with jsonlines.open(doc_meta_path, "r") as reader:
        for entry in reader:
            doc_id = entry.get("doc_id")
            if doc_id:
                # Support redirect: point this doc_id to its canonical one if redirect_to is set
                redirect = entry.get("redirect_to")
                if redirect:
                    doc_meta_lookup[doc_id] = {"redirect_to": redirect}
                    continue
                doc_meta_lookup[doc_id] = {
                    "url": entry.get("url"),
                    "committee": entry.get("committee"),
                    "meeting_date": entry.get("meeting_date"),
                    "filename": entry.get("filename"),
                    "document_type": entry.get("document_category", "N/A")
                }

    return metadata_df, doc_meta_lookup

metadata_df, doc_meta_lookup = load_data()
# Debug: Show unique Committees for inspection
# if "committee" in metadata_df.columns and metadata_df["committee"].notna().any():
#     st.write("🔍 Unique Committees:", sorted(metadata_df["committee"].dropna().unique()))
# else:
#     st.write("🔍 Unique Committees: No 'committee' column found")

# --- Sidebar Filters ---
# Determine committee options based on doc_meta_lookup
all_committees = sorted(set(
    meta["committee"]
    for meta in doc_meta_lookup.values()
    if isinstance(meta, dict) and meta.get("committee") not in (None, "", "N/A")
))
if all_committees:
    all_committees = ["All"] + all_committees
else:
    all_committees = ["All"]

st.sidebar.title("Filters")
top_k = st.sidebar.slider("Number of chunks to send to GPT", min_value=1, max_value=20, value=5)
context_window = st.sidebar.slider("Adjacent chunks to include", min_value=0, max_value=3, value=0)
committee = st.sidebar.selectbox("Committee", all_committees)

embedding_model = st.sidebar.selectbox(
    "Embedding model",
    ["text-embedding-3-small", "text-embedding-3-large"],
    index=0
)

embedding_index_path = {
    "text-embedding-3-small": "data/embeddings/council_index_small.faiss",
    "text-embedding-3-large": "data/embeddings/council_index_large.faiss"
}[embedding_model]

index = faiss.read_index(embedding_index_path)

chat_model = st.sidebar.selectbox(
    "Chat model",
    ["gpt-4o-mini", "gpt-3.5-turbo", "gpt-4"],
    index=0
)

temperature = st.sidebar.slider("GPT Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1)

# Add slider for number of distinct documents to show
max_display = st.sidebar.slider("Number of documents to show", min_value=1, max_value=10, value=5)

# --- Question Input ---
st.title("🧠 CouncilBrain")

tab_titles = ["Ask a Question", "AI Summary"]
tabs = st.tabs(tab_titles)

with tabs[0]:
    st.markdown("""
        <style>
            .block-container {
                padding-top: 3rem !important;
                padding-bottom: 3rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)
    question = st.text_input("Ask a question about council documents:")

    # Add a new "View the Results" button directly below the text input box for the question
    preview_chunks = st.button("View the Results", key="preview_chunks")

    system_prompt = '''
You are a Council Intelligence Analyst. Your job is to explain the Council’s latest thinking on a topic using real documents.

Instructions:
1. Compare multiple documents (agenda items and summaries) from different committees and years.
2. Identify what has changed over time.
3. Cite each source explicitly.
4. If sources conflict, highlight that.

If the same idea appears many times, say: “This is consistent across several documents (e.g., [2024 Cabinet], [2023 Council])…”

If only one strong source is found, say: “Only one detailed agenda item was found, from [Committee, Year]…”

Do not speculate. Be clear about uncertainty or missing details.
'''

    def build_user_prompt(query, context_text):
        return f"""Answer the following question using only the information in the provided context.

Question:
{query}

Relevant Documents:
{context_text}

Answer:"""

    if preview_chunks and question:
        log_query(question, page="Ask GPT")
        with st.spinner("🔎 Searching..."):
            import jsonlines

            # Embed the query
            def get_embedding(text, model=embedding_model):
                response = client.embeddings.create(input=[text], model=model)
                return response.data[0].embedding

            query_vector = np.array(get_embedding(question)).astype("float32").reshape(1, -1)

            # Load agenda and pdf summary metadata
            with jsonlines.open("data/embeddings/agendas/metadata_agenda.jsonl", "r") as reader:
                agenda_meta = pd.DataFrame(reader)
            with jsonlines.open("data/embeddings/pdf_summaries/metadata_pdf_summaries.jsonl", "r") as reader:
                pdf_meta = pd.DataFrame(reader)

            # Load FAISS indexes
            agenda_index = faiss.read_index("data/embeddings/agendas/agenda_index.faiss")
            pdf_index = faiss.read_index("data/embeddings/pdf_summaries/pdf_summary_index.faiss")

            # Search both
            agenda_D, agenda_I = agenda_index.search(query_vector, 100)
            pdf_D, pdf_I = pdf_index.search(query_vector, 100)

            agenda_hits = agenda_meta.iloc[agenda_I[0]].copy()
            agenda_hits["score"] = agenda_D[0]
            agenda_hits["source_type"] = "agenda"

            # Merge agenda metadata for committee_name, meeting_date, item_title
            with jsonlines.open("data/metadata/agendas.jsonl", "r") as reader:
                agenda_full_meta = pd.DataFrame(reader)
            agenda_full_meta["meeting_date"] = pd.to_numeric(agenda_full_meta["meeting_date"], errors="coerce")
            agenda_hits["agenda_id"] = agenda_hits["chunk_id"]
            agenda_hits = agenda_hits.merge(
                agenda_full_meta[["agenda_id", "committee_name", "meeting_date", "item_title"]],
                how="left",
                on="agenda_id"
            )
            # After merging, assign and clean up the correct date column
            agenda_hits["meeting_date"] = agenda_hits["meeting_date_y"]
            agenda_hits = agenda_hits.drop(columns=[col for col in ["meeting_date_x", "meeting_date_y"] if col in agenda_hits.columns])

            pdf_hits = pdf_meta.iloc[pdf_I[0]].copy()
            pdf_hits["score"] = pdf_D[0]
            pdf_hits["source_type"] = "pdf"

            # Deduplicate and trim agenda and pdf results separately
            agenda_hits = agenda_hits.sort_values("score").drop_duplicates(subset=["chunk_id"]).head(5)
            pdf_hits = pdf_hits.sort_values("score").drop_duplicates(subset=["doc_id"]).head(5)

            # Merge document metadata only into pdf results
            with jsonlines.open("data/metadata/documents.jsonl", "r") as reader:
                doc_meta = pd.DataFrame(reader)
            pdf_hits = pdf_hits.merge(doc_meta, on="doc_id", how="left")

            # Combine both types again
            combined = pd.concat([agenda_hits, pdf_hits], ignore_index=True)

            # Build GPT context with inline citations (replacing footnote-style citations)
            context = ""
            # footnotes = []
            # footnote_counter = 1
            # footnote_refs = []
            for _, row in combined.iterrows():
                label = "Agenda Item" if row["source_type"] == "agenda" else "PDF Summary"
                title = row.get("item_title") if row["source_type"] == "agenda" else row.get("display_title", "Untitled")
                raw_date = row.get("meeting_date", None)
                meeting_str = "N/A"
                try:
                    if isinstance(raw_date, (float, int)) and not pd.isnull(raw_date):
                        meeting_dt = pd.to_datetime(int(raw_date), unit="ms", errors="coerce")
                        meeting_str = meeting_dt.strftime("%-d %b %Y") if pd.notnull(meeting_dt) else "N/A"
                except Exception:
                    meeting_str = str(raw_date)
                source_note = f"{row.get('committee_name', 'Unknown Committee')}, {meeting_str}"
                heading = f"{label}: {title} ({source_note})\n{row.get('text', '')}\n"
                context += heading + "\n---\n\n"
                # footnote_counter += 1
            # context += "\n".join(footnotes)

            prompt = build_user_prompt(question, context)
            response = client.chat.completions.create(
                model=chat_model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            st.subheader("GPT Answer")
            st.markdown(response.choices[0].message.content)
            with st.expander("📤 What was sent to ChatGPT"):
                st.code(prompt, language="markdown")

with tabs[1]:
    st.info("The AI Summary tab is under construction.")
