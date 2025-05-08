# app/streamlit_app.py

import streamlit as st
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

# Add slider for number of distinct documents to show
max_display = st.sidebar.slider("Number of documents to show", min_value=1, max_value=10, value=5)

# --- Question Input ---
st.title("Council Assistant")
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

system_prompt = """
You are Council Assistant, an AI designed to summarize and answer questions using official local government documents.
Your task is to provide a concise and factual answer based solely on the excerpts below.

Instructions:
- Base your answer only on the information provided in the documents.
- Do not make assumptions or use outside knowledge.
- If the documents provide only partial or trend-based information, summarize that.
- If the information is entirely insufficient or ambiguous, say: "The answer cannot be determined from the documents provided."
- Your answer should be clear, direct, and structured in full sentences.
"""

def build_user_prompt(query, context_text):
    return f"""Answer the following question using only the information in the provided context.

Question:
{query}

Relevant Documents:
{context_text}

Answer:"""

if preview_chunks and question:
    with st.spinner("🔎 Searching..."):
        def get_embedding(text, model=embedding_model):
            response = client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding

        query_vector = np.array(get_embedding(question)).astype("float32").reshape(1, -1)
        top_k_chunks = max_display * 3
        distances, indices = index.search(query_vector, top_k_chunks)

        selected_rows = metadata_df.iloc[indices[0]].copy()
        selected_rows["similarity"] = 1 - distances[0]  # cosine similarity = 1 - distance

        # Merge with metadata_df to enrich fields like committee and meeting_date
        merge_columns = ["doc_id", "committee", "meeting_date", "filename"]
        available_columns = [col for col in merge_columns if col in metadata_df.columns]

        selected_rows = selected_rows.merge(
            metadata_df[available_columns],
            on="doc_id",
            how="left",
            suffixes=("", "_y")
        )
        # Resolve potential duplicate columns
        for col in ["committee", "meeting_date", "filename"]:
            if f"{col}_y" in selected_rows.columns:
                selected_rows[col] = selected_rows[f"{col}_y"]
                selected_rows.drop(columns=[f"{col}_y"], inplace=True)

        # Load context with improved logging for debugging
        chunks = []
        for _, row in selected_rows.iterrows():
            source_file = row.get("source_file")
            chunk_id = row.get("chunk_id")

            if not source_file or not os.path.isfile(source_file):
                st.warning(f"⚠️ Source file missing or invalid: {source_file}")
                continue

            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    chunk_data = json.load(f)
                    start = max(0, chunk_id - context_window)
                    end = min(len(chunk_data), chunk_id + context_window + 1)
                    for i in range(start, end):
                        chunks.append(chunk_data[i]["text"])
            except Exception as e:
                st.warning(f"⚠️ Error loading chunk from {source_file}: {e}")

        # Score chunks by similarity and deduplicate
        selected_rows["text"] = ""
        for i, row in selected_rows.iterrows():
            source_file = row.get("source_file")
            chunk_id = row.get("chunk_id")
            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    chunk_data = json.load(f)
                    row_text = chunk_data[chunk_id]["text"]
                    selected_rows.at[i, "text"] = row_text
            except:
                continue

        # Remove duplicates by text
        selected_rows = selected_rows.drop_duplicates(subset="text")

        # Keep top-N most similar chunks
        selected_rows = selected_rows.sort_values(by="similarity", ascending=False).head(top_k)
        chunks = selected_rows["text"].tolist()

        # Generate GPT answer immediately after chunks are computed
        context = "\n\n---\n\n".join(chunks)
        prompt = build_user_prompt(question, context)
        response = client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        st.subheader("GPT Answer")
        st.markdown(response.choices[0].message.content)

        if preview_chunks:
            # Moved Relevant Documents block above Preview Chunks block
            # Relevant Documents block
            # Ensure required columns are present to avoid KeyError during groupby
            for col in ['filename', 'committee', 'meeting_date']:
                if col not in selected_rows.columns:
                    selected_rows[col] = "[unknown]"

            # Optional field: document_type
            agg_dict = {
                "meeting_date": "first",
                "committee": "first",
                "filename": "first",
                "chunk_id": list,
                "similarity": ["count", "mean"]
            }
            grouped = selected_rows.groupby("doc_id").agg(agg_dict)
            grouped.columns = ["meeting_date", "committee", "filename", "chunk_id", "hit_count", "avg_similarity"]
            grouped["document_score"] = grouped["hit_count"] * grouped["avg_similarity"]
            grouped = grouped.sort_values(by="document_score", ascending=False).reset_index()
            grouped = grouped.head(max_display)

            from urllib.parse import quote

            table_rows = []
            for i, row in grouped.iterrows():
                redirect_id = doc_meta_lookup.get(row["doc_id"], {}).get("redirect_to", row["doc_id"])
                meta = doc_meta_lookup.get(redirect_id, {})
                safe_url = quote(meta.get("url", ""), safe=':/?&=')
                # Fallback: avoid crash if "page_num" is missing
                mentioned_pages = "N/A"
                table_rows.append({
                    "Rank": i + 1,
                    "Meeting Date": meta.get("meeting_date", "N/A"),
                    "Committee": meta.get("committee", "N/A"),
                    "File": f"[{os.path.basename(meta.get('filename', '[unknown]'))}]({safe_url})",
                    "Document Type": meta.get("document_type", "N/A"),
                    "Mentioned on page(s)": mentioned_pages,
                    "Match Score": f"{row['document_score']:.2f}",
                    "Chunks Matched": row["hit_count"],
                    "Avg Similarity": f"{row['avg_similarity']:.2f}",
                })

            df = pd.DataFrame(table_rows)
            df = df.drop_duplicates(subset="File").head(max_display)

            # Generate HTML table
            def make_clickable(link_text, url):
                return f'<a href="{url}" target="_blank">{link_text}</a>'

            rows = []
            for _, row in df.iterrows():
                url = row["File"].split("](")[-1].rstrip(")")
                text = row["File"].split("[")[-1].split("]")[0]
                link = make_clickable(text, url)
                rows.append(f"<tr><td>{row['Rank']}</td><td>{row['Meeting Date']}</td><td>{row['Committee']}</td><td>{link}</td><td>{row['Document Type']}</td><td>{row['Mentioned on page(s)']}</td><td>{row['Match Score']}</td><td>{row['Chunks Matched']}</td><td>{row['Avg Similarity']}</td></tr>")

            table_html = f"""
            <table>
                <thead>
                    <tr><th>Rank</th><th>Meeting Date</th><th>Committee</th><th>File</th><th>Document Type</th><th>Mentioned on page(s)</th><th>Match Score</th><th>Chunks Matched</th><th>Avg Similarity</th></tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
            """
            st.subheader("Relevant Documents")
            st.markdown(table_html, unsafe_allow_html=True)

            st.subheader("🧪 Preview Chunks to be Sent")
            from urllib.parse import quote
            for idx, chunk in enumerate(chunks):
                doc_id = selected_rows.iloc[idx]["doc_id"]
                redirect_id = doc_meta_lookup.get(doc_id, {}).get("redirect_to", doc_id)
                meta = doc_meta_lookup.get(redirect_id, {})
                doc_name = os.path.basename(meta.get("filename", "[unknown]"))
                url = meta.get("url", "")
                safe_url = quote(url, safe=':/?&=')
                st.text_area(
                    label=f"{doc_name} – {meta.get('meeting_date', '')}",
                    value=chunk,
                    height=150,
                    label_visibility="collapsed"
                )
                st.markdown(
                    f'<div style="margin-top:-15px; margin-bottom:30px;"><small><a href="{safe_url}" target="_blank">{doc_name}</a> – {meta.get("meeting_date", "N/A")}</small></div>',
                    unsafe_allow_html=True
                )
