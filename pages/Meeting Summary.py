import streamlit as st
import pandas as pd
from pathlib import Path
import jsonlines
from urllib.parse import quote
import uuid
import json
from datetime import datetime
from scripts.utils.meeting_cleaning import normalize_committee

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
    path = Path("data/meetings/meetings_metadata.jsonl")
    with jsonlines.open(path, "r") as reader:
        records = list(reader)
    df = pd.DataFrame(records)
    df["committee_name"] = df["committee_name"].apply(normalize_committee)
    return df

df = load_metadata()

st.markdown("## Select a Committee and Meeting")

df["meeting_date"] = pd.to_datetime(df["meeting_date"], errors="coerce")
committees = sorted(df["committee_name"].dropna().unique())
committee_names = [c.replace("_", " ").title() for c in committees]
committee_map = dict(zip(committee_names, committees))

selected_committee_display = st.selectbox("Committee", committee_names)
selected_committee = committee_map[selected_committee_display]

# Filter to only available dates for this committee
raw_dates = df[df["committee_name"] == selected_committee]["meeting_date"].dropna().unique()
formatted_dates = sorted([d.strftime("%Y-%m-%d") for d in raw_dates], reverse=True)
date_map = {d.strftime("%Y-%m-%d"): d for d in raw_dates}
selected_date_str = st.selectbox("Meeting Date", formatted_dates)
selected_date = date_map[selected_date_str]

if st.button("View Summary"):
    st.markdown(f"# {selected_committee_display}")
    st.markdown(f"### Meeting on {selected_date.strftime('%-d %B %Y')}")

    # Show link to original meeting page
    meeting_row = df[
        (df["committee_name"] == selected_committee) &
        (df["meeting_date"] == selected_date)
    ].iloc[0]
    mid = meeting_row.get("web_meeting_code")
    if mid:
        st.markdown(f"[View this meeting on Kent.gov.uk](https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={mid})")

    # === Full Agenda Items ===
    from pathlib import Path
    import json

    st.markdown("#### Full Agenda for This Meeting")

    MEETINGS_PATH = Path("data/meetings/meetings_metadata.jsonl")
    agenda_items = []
    if MEETINGS_PATH.exists():
        with open(MEETINGS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if (
                        record.get("meeting_date") == selected_date.strftime("%Y-%m-%d") and
                        record.get("committee_name", "").lower().replace("–", "-") == selected_committee_display.lower()
                    ):
                        agenda_items = record.get("agenda_items", [])
                        break
                except:
                    continue

    if agenda_items:
        for item in agenda_items:
            title = item.get("item_title", "").strip()
            number = item.get("item_number", "").strip()
            st.markdown(f"- **{number}** {title}")
    else:
        st.info("No agenda items found in the metadata for this meeting.")

    # Filter relevant documents
    docs_df = df[
        (df["committee_name"] == selected_committee) &
        (df["meeting_date"] == selected_date)
    ].copy()

    if docs_df.empty:
        st.info("No documents found for that meeting.")
    else:
        filename_col = docs_df["filename"] if "filename" in docs_df.columns else pd.Series([""] * len(docs_df), index=docs_df.index)
        url_col = docs_df["url"] if "url" in docs_df.columns else pd.Series([""] * len(docs_df), index=docs_df.index)

        agenda_docs = docs_df[
            filename_col.str.lower().str.contains("agenda", na=False) |
            url_col.str.lower().str.contains("agenda", na=False)
        ]

        minutes_docs = docs_df[
            filename_col.str.lower().str.contains("minute", na=False) |
            url_col.str.lower().str.contains("minute", na=False)
        ]

        shown_doc_ids = set(agenda_docs["doc_id"]).union(set(minutes_docs["doc_id"]))
        other_docs = docs_df[~docs_df["doc_id"].isin(shown_doc_ids)]

        if not agenda_docs.empty:
            st.markdown("#### Agenda Documents")
            for _, row in agenda_docs.iterrows():
                file_url = quote(row.get("url", ""), safe=':/?&=')
                st.markdown(f"- [{row.get('filename', '')}]({file_url})")

        if not minutes_docs.empty:
            st.markdown("#### Minutes Documents")
            for _, row in minutes_docs.iterrows():
                file_url = quote(row.get("url", ""), safe=':/?&=')
                st.markdown(f"- [{row.get('filename', '')}]({file_url})")

        if not other_docs.empty:
            st.markdown("#### Other Documents")
            for _, row in other_docs.iterrows():
                file_url = quote(row.get("url", ""), safe=':/?&=')
                doc_type_display = row.get("document_category", "Document").replace("_", " ").title()
                st.markdown(f"- **{doc_type_display}:** [{row.get('filename', '')}]({file_url})")
