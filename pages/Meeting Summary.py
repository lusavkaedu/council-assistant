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

st.title("Council Meeting Summary")

# --- Load Metadata ---
@st.cache_data
def load_metadata():
    path = Path("data/document_metadata/raw_scraped_metadata.jsonl")
    with jsonlines.open(path, "r") as reader:
        records = list(reader)
    return pd.DataFrame(records)

df = load_metadata()

st.sidebar.header("Select Meeting")

# Committee selector
committees = sorted(df["committee"].dropna().unique())
committee_names = [c.replace("_", " ").title() for c in committees]
committee_map = dict(zip(committee_names, committees))
selected_committee_display = st.sidebar.selectbox("Committee", committee_names)
selected_committee = committee_map[selected_committee_display]

# Date selector
df["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce")
raw_dates = df[df["committee"] == selected_committee]["meeting_date"].dropna().unique()
formatted_dates = sorted([d.strftime("%Y-%m-%d") for d in raw_dates], reverse=True)
date_map = {d.strftime("%Y-%m-%d"): d for d in raw_dates}
selected_date_str = st.sidebar.selectbox("Meeting Date", formatted_dates)
selected_date = date_map[selected_date_str]

# Select button
selected = st.sidebar.button("Select")

if selected:
    st.markdown(f"### {selected_committee_display} meeting on {selected_date.strftime('%-d %B %Y')}")

    docs_df = df[
        (df["committee"] == selected_committee) &
        (df["meeting_date"] == selected_date)
    ].copy()

    if docs_df.empty:
        st.info("No documents found for that meeting.")
    else:
        agenda_docs = docs_df[
            docs_df["filename"].str.lower().str.contains("agenda", na=False) |
            docs_df["url"].str.lower().str.contains("agenda", na=False)
        ]
        minutes_docs = docs_df[
            docs_df["filename"].str.lower().str.contains("minute", na=False) |
            docs_df["url"].str.lower().str.contains("minute", na=False)
        ]
        shown_doc_ids = set(agenda_docs["doc_id"]).union(set(minutes_docs["doc_id"]))
        other_docs = docs_df[~docs_df["doc_id"].isin(shown_doc_ids)]

        if not agenda_docs.empty:
            st.markdown("#### 🗂️ Agenda Documents")
            for _, row in agenda_docs.iterrows():
                file_url = quote(row["url"], safe=':/?&=')
                st.markdown(f"- [{row.get('filename')}]({file_url})")

        if not minutes_docs.empty:
            st.markdown("#### 📄 Minutes Documents")
            for _, row in minutes_docs.iterrows():
                file_url = quote(row["url"], safe=':/?&=')
                st.markdown(f"- [{row.get('filename')}]({file_url})")

        table_data = []
        for _, row in other_docs.iterrows():
            file_url = quote(row["url"], safe=':/?&=')
            doc_type_display = row.get("document_category", "N/A").replace("_", " ").title()
            page_count = row.get("page_count", "N/A") if "page_count" in row else "N/A"

            table_data.append({
                "Filename": f"[{row.get('filename')}]({file_url})",
                "Pages": page_count,
                "Document Type": doc_type_display
            })

        st.markdown(pd.DataFrame(table_data).to_markdown(index=False), unsafe_allow_html=True)
