# app/streamlit_app.py

import streamlit as st
import json
import openai
import faiss
import numpy as np
import os
import pandas as pd

# --- Load environment ---
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Load metadata and FAISS index ---
@st.cache_resource
def load_data():
    metadata_df = pd.read_pickle("data/merged_metadata.pkl")
    index = faiss.read_index("data/embeddings/council_index_large.faiss")
    return metadata_df, index

metadata_df, index = load_data()
# Debug: Show unique Committees for inspection
# if "committee" in metadata_df.columns and metadata_df["committee"].notna().any():
#     st.write("🔍 Unique Committees:", sorted(metadata_df["committee"].dropna().unique()))
# else:
#     st.write("🔍 Unique Committees: No 'committee' column found")

# --- Sidebar Filters ---
# Determine committee options based on metadata
if "committee" in metadata_df.columns and metadata_df["committee"].notna().any():
    all_committees = sorted(set(metadata_df["committee"].dropna().unique()) - {"", "N/A"})
    all_committees = ["All"] + all_committees
else:
    all_committees = ["All"]

st.sidebar.title("Filters")
top_k = st.sidebar.slider("Number of documents to retrieve", min_value=1, max_value=20, value=5)
committee = st.sidebar.selectbox("Committee", all_committees)

# --- Question Input ---
st.title("Council Assistant")
question = st.text_input("Ask a question about council documents:")

system_prompt = f"""
   You are Council Assistant, an AI designed to summarize and answer questions using official local government documents. Your task is to provide a concise and factual answer based solely on the excerpts below.
"""

def build_user_prompt(query, context_text):
    return f"""Answer the following question using only the information in the provided context.

Question:
{query}

Relevant Documents:
{context_text}

Answer:"""

if question:
    with st.spinner("🔎 Searching..."):
        def get_embedding(text, model="text-embedding-3-large"):
            response = client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding

        query_vector = np.array(get_embedding(question)).astype("float32").reshape(1, -1)
        distances, indices = index.search(query_vector, top_k)

        selected_rows = metadata_df.iloc[indices[0]].copy()
        selected_rows["chunk_id"] = selected_rows["chunk_id"].astype(int)

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
                    if 0 <= chunk_id < len(chunk_data):
                        chunks.append(chunk_data[chunk_id]["text"])
                    else:
                        st.warning(f"⚠️ Invalid chunk_id {chunk_id} for file: {source_file}")
            except Exception as e:
                st.warning(f"⚠️ Error loading chunk from {source_file}: {e}")

        if chunks:
            context = "\n\n---\n\n".join(chunks)
        else:
            context = "No relevant excerpts were found."
        st.text_area("🧾 Debug: Context Sent to Model", context, height=300)
        prompt = build_user_prompt(question, context)
        st.text_area("🧾 Debug: Prompt Sent to Model", prompt, height=300)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )

        st.subheader("GPT Answer")
        st.markdown(response.choices[0].message.content)

        st.subheader("Relevant Documents")

        # Optional field: document_type
        agg_dict = {
            'meeting_date': lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0],
            'committee': lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0],
            'filename': lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0],
            'chunk_id': list,
        }
        if 'document_type' in selected_rows.columns:
            agg_dict['document_type'] = lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]
        grouped = selected_rows.groupby('doc_id').agg(agg_dict).reset_index()

        from urllib.parse import quote

        for i, row in grouped.iterrows():
            meeting_date = row["meeting_date"] if pd.notna(row["meeting_date"]) else "N/A"
            committee = row["committee"] if pd.notna(row["committee"]) else "N/A"
            filename = row["filename"] if pd.notna(row["filename"]) else "N/A"
            chunk_ids = row["chunk_id"]

            # Retrieve URL from metadata_df
            url = metadata_df.loc[metadata_df["doc_id"] == row["doc_id"], "url"]
            url = url.iloc[0] if not url.empty else "[insert URL from metadata if available]"

            # Format page numbers instead of chunk_ids
            page_nums = metadata_df.loc[metadata_df["doc_id"] == row["doc_id"], "page_num"]
            page_nums = [p for p in page_nums if pd.notna(p)]
            if page_nums:
                sorted_pages = sorted(set(int(p) for p in page_nums))
                pages_str = ", ".join(str(p) for p in sorted_pages)
            else:
                pages_str = "N/A"

            # Safely encode the URL to handle spaces and special characters
            safe_url = quote(url, safe=':/?&=')

            st.markdown(f"""
            **Rank {i+1}**

            Meeting Date: {meeting_date}  
            Committee: {committee}  
            File: [{os.path.basename(filename)}]({safe_url})  
            Document Type: {row.get("document_type", "N/A")}  
            Mentioned on page(s): {pages_str}
            """)
            # <!--
            # > {text_snippet}...
            # -->
