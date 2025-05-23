import streamlit as st
import pandas as pd
from pathlib import Path
import jsonlines
from urllib.parse import quote
import uuid
import json
from datetime import datetime

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

st.set_page_config(page_title="Document Search", layout="wide")
st.title("Document Search")

# --- Load Metadata ---
@st.cache_data
def load_metadata():
    path = Path("data/document_metadata/raw_scraped_metadata.jsonl")
    with jsonlines.open(path, "r") as reader:
        records = list(reader)
    return pd.DataFrame(records)

df = load_metadata()

# --- Embedding-based semantic search setup ---
import numpy as np
from openai import OpenAI
import faiss
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load agenda item metadata
@st.cache_data
def load_chunk_metadata():
    import jsonlines
    with jsonlines.open("data/embeddings/agendas/metadata_agenda.jsonl", "r") as reader:
        records = list(reader)
    return pd.DataFrame(records)

chunk_df = load_chunk_metadata()

# Load FAISS index for agenda items
@st.cache_resource
def load_index():
    return faiss.read_index("data/embeddings/agendas/agenda_index.faiss")

index = load_index()

# --- Top-Level Keyword Search ---
query = st.text_input(
    "Search agenda items for a keyword or phrase",
    placeholder="What the council is doing to address disruption to traffic caused by frequent road closures? Many residents are complaining about it."
)

if query and len(df) > 0:
    log_query(query, page="Document Search")
    # --- Sidebar Filters ---

    st.sidebar.header("Filters")

    # Committee filter
    committees = sorted(df["committee"].dropna().unique())
    selected_committee = st.sidebar.selectbox("Committee", ["All"] + committees)

    # Document type filter
    doc_types = sorted(df["document_category"].dropna().unique())
    selected_type = st.sidebar.selectbox("Document type", ["All"] + doc_types)

    max_candidates = min(50, len(df))  # Cap max to a reasonable limit (e.g., 50)
    max_display = st.sidebar.slider("Documents to display", min_value=1, max_value=max_candidates, value=min(5, max_candidates))

    df["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce")
    min_date = df["meeting_date"].min()
    max_date = df["meeting_date"].max()
    start_date = st.sidebar.date_input("Start date", min_date)
    end_date = st.sidebar.date_input("End date", max_date)

    # --- Apply Filters ---

    # --- Embedding-based semantic search with Ask GPT-style ranking on agenda items ---
    with st.spinner("Searching agenda items..."):
        query_embedding = client.embeddings.create(input=[query], model="text-embedding-3-small").data[0].embedding
        query_vector = np.array(query_embedding).astype("float32").reshape(1, -1)
        distances, indices = index.search(query_vector, 100)

        chunk_hits = chunk_df.iloc[indices[0]].copy()
        chunk_hits["similarity"] = 1 - distances[0]
        chunk_hits["doc_id"] = chunk_hits["doc_id"].astype(str)

        # Aggregate scoring similar to Ask GPT
        grouped = chunk_hits.groupby("doc_id").agg(
            hit_count=("similarity", "count"),
            avg_similarity=("similarity", "mean")
        )
        grouped["document_score"] = grouped["hit_count"] * grouped["avg_similarity"]
        grouped = grouped.sort_values(by="document_score", ascending=False).reset_index()

        st.write("doc_id in chunk hits (top 5):", chunk_hits["doc_id"].drop_duplicates().head().tolist())

        # Load agenda metadata and join to document scores
        agenda_df = pd.read_json("data/processed_register/agenda_manifest.jsonl", lines=True)
        agenda_df["doc_id"] = agenda_df["doc_id"].astype(str)
        st.write("doc_id in agenda metadata (top 5):", agenda_df["doc_id"].drop_duplicates().head().tolist())
        filtered_df = agenda_df[agenda_df["doc_id"].isin(grouped["doc_id"])].copy()
        filtered_df = filtered_df.merge(grouped[["doc_id", "document_score"]], on="doc_id", how="left")
        filtered_df = filtered_df.sort_values(by="document_score", ascending=False)
        filtered_df["meeting_date"] = pd.to_datetime(filtered_df["meeting_date"], errors="coerce")

    if selected_committee != "All":
        filtered_df = filtered_df[filtered_df["committee"] == selected_committee]

    filtered_df = filtered_df[
        (filtered_df["meeting_date"] >= pd.to_datetime(start_date)) &
        (filtered_df["meeting_date"] <= pd.to_datetime(end_date))
    ]

    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["document_category"] == selected_type]

    # --- Display Results ---
    st.markdown(f"### Results ({len(filtered_df)} documents found)")

    if not filtered_df.empty:
        # Sorting controls (moved to sidebar)
        sort_column = st.sidebar.selectbox(
            "Sort by",
            ["Relevance", "Meeting Date", "Committee", "Filename", "Document Type"],
            index=0
        )
        sort_order = st.sidebar.radio("Order", ["Ascending", "Descending"], horizontal=True)
        ascending = sort_order == "Ascending"
        sort_col_map = {
            "Relevance": "document_score",
            "Meeting Date": "meeting_date",
            "Committee": "committee",
            "Filename": "filename",
            "Document Type": "document_category"
        }
        filtered_df.sort_values(by=sort_col_map[sort_column], ascending=ascending, inplace=True)

        filtered_df = filtered_df.head(max_display)

        table_data = []
        for _, row in filtered_df.iterrows():
            file_url = quote(row["url"], safe=':/?&=')
            committee_display = row.get("committee", "N/A").replace("_", " ").title()
            doc_type_display = row.get("document_category", "N/A").replace("_", " ").title()

            table_data.append({
                "Meeting Date": row.get("meeting_date", "N/A").date() if pd.notna(row.get("meeting_date")) else "N/A",
                "Committee": committee_display,
                "Filename": f"[{row.get('filename')}]({file_url})",
                "Document Type": doc_type_display
            })

        st.markdown(pd.DataFrame(table_data).to_markdown(index=False), unsafe_allow_html=True)
    else:
        st.info("No documents match the selected filters.")

    # --- Preview top matching agenda items ---
    st.subheader("📄 Best matching agenda items preview:")

    if chunk_hits.empty:
        st.info("No matching agenda items available for preview.")
        st.stop()

    for _, row in filtered_df.iterrows():
        doc_id = row["doc_id"]
        doc_title = row["filename"]
        doc_url = row.get("url", "")
        safe_url = quote(doc_url, safe=':/?&=')
        similarity_threshold = 0.83
        doc_chunks = chunk_hits[chunk_hits["doc_id"] == doc_id].copy()
        doc_chunks["similarity"] = pd.to_numeric(doc_chunks["similarity"], errors="coerce")
        similar_chunks = doc_chunks[doc_chunks["similarity"] >= similarity_threshold].sort_values(by="similarity", ascending=False)

        if not similar_chunks.empty:
            top_chunks = similar_chunks
        else:
            # fallback: show top chunk even if below threshold
            top_chunks = doc_chunks.sort_values(by="similarity", ascending=False)

        meeting_date = row.get("meeting_date", "N/A")
        if pd.notna(meeting_date) and hasattr(meeting_date, 'strftime'):
            meeting_date = meeting_date.strftime("%-d %B %Y")
        committee = row.get("committee", "N/A")
        committee_formatted = committee.replace("_", " ").title()
        st.markdown(f"**Preview from [{doc_title}]({safe_url}), considered by the {committee_formatted} on {meeting_date}:**")

        for _, c in top_chunks.iterrows():
            similarity = c["similarity"]
            st.markdown(f"Matched agenda item with similarity {similarity:.2f}")

    # --- Placeholder for upcoming PDF document semantic search ---
    st.subheader("📄 PDF Document Matches (Coming Soon)")
    st.info("This section will display semantic matches from full council PDF documents once the FAISS index is generated. Please check back shortly.")

    # TODO: Load pdf_summary_embeddings.jsonl and agenda_index.faiss once ready
    # Perform similar vector search and display PDF-level matches here
