import streamlit as st
st.set_page_config(page_title="Committees", layout="wide")
import json
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from scripts.utils.meeting_cleaning import clean_data, normalize_committee  # Adjust path if needed


st.title("Council Committees")

# Load cleaned meetings data
MEETINGS_PATH = Path("data/meetings/meetings_metadata.jsonl")
if MEETINGS_PATH.exists():
    cleaned_data = clean_data(MEETINGS_PATH)
else:
    st.warning("Meetings metadata not found. Please scrape data first.")
    cleaned_data = pd.DataFrame()

# Load committee metadata
COMMITTEE_META_PATH = Path("data/metadata/committees.jsonl")
committee_metadata = {}
if COMMITTEE_META_PATH.exists():
    with open(COMMITTEE_META_PATH, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            canonical = entry["canonical_name"]
            committee_metadata[canonical] = entry

# Normalize committee_name once after loading cleaned_data
if not cleaned_data.empty and "committee_name" in cleaned_data.columns:
    cleaned_data["normalized_committee_name"] = cleaned_data["committee_name"].apply(normalize_committee)


available_committees = sorted(cleaned_data['committee_name'].dropna().unique())

# Build committee summary table
committee_summary = (
    cleaned_data.explode("agenda_items")
    .dropna(subset=["committee_name", "meeting_date", "agenda_items"])
    .assign(pdf_count=lambda df: df["agenda_items"].apply(lambda x: len(x.get("pdf_urls", [])) if isinstance(x, dict) else 0))
    .groupby("committee_name")
    .agg(total_meetings=("meeting_date", "nunique"), total_documents=("pdf_count", "sum"))
    .reset_index()
)

# Default to homepage view unless user has selected a committee
if "selected_committee" not in st.session_state:
    # Try to grab from URL params (if user clicked a link)
    query_params = st.query_params
    if "selected_committee" in query_params:
        st.session_state["selected_committee"] = query_params["selected_committee"][0]

if "selected_committee" not in st.session_state:
    # Create a copy and embed links in the Committee Name column
    display_df = committee_summary.rename(columns={
        "committee_name": "Committee Name",
        "total_meetings": "Meetings Available",
        "total_documents": "Documents Available"
    }).reset_index(drop=True)

    display_df["Committee Name"] = display_df["Committee Name"].apply(
        lambda name: f"<a href='?selected_committee={name}' target='_self'>{name}</a>"
    )

    st.markdown("### Browse Council Committees")
    st.markdown(
        display_df.to_html(escape=False, index=False),
        unsafe_allow_html=True
    )
    st.stop()

# Sidebar filters
selected_committee = st.session_state.get("selected_committee") or ""
selected_committee = selected_committee.strip()
st.sidebar.markdown("## Committee Selection")
if st.sidebar.button("← Back to All Committees"):
    st.session_state.pop("selected_committee", None)
    st.query_params.clear()  # Clear any ?selected_committee param
    st.rerun()

st.sidebar.markdown("## Agenda Filters")
# Date range selector
default_start = cleaned_data["meeting_date"].min()
default_end = cleaned_data["meeting_date"].max()
start_date = st.sidebar.date_input("Start Date", default_start)
end_date = st.sidebar.date_input("End Date", default_end)
# Keyword search
search_keyword = st.sidebar.text_input("Search Agenda Item", value="")

normalized_committee = normalize_committee(selected_committee)

# Content only appears if a selection is made
if not selected_committee or not isinstance(selected_committee, str):
    st.warning("No valid committee selected.")
    st.stop()

st.markdown(f"## {selected_committee}")

if selected_committee in committee_metadata:
    meta = committee_metadata[selected_committee]
    st.markdown(f"*Committee ID: `{meta['committee_id']}`*")
    st.markdown(f"*Council: `{meta['council_code']}`*")

# Committee Agenda Items - Past 12 Months
st.markdown("### Recent Agenda Items (Past 12 Months)")

cleaned_data["meeting_date"] = pd.to_datetime(cleaned_data["meeting_date"], errors="coerce")
today = datetime.now()
one_year_ago = today - timedelta(days=365)

# Separate past and future meetings
normalized_committee = normalize_committee(selected_committee)

past_meetings = cleaned_data[
    (cleaned_data["normalized_committee_name"] == normalized_committee) &
    (cleaned_data["meeting_date"] >= pd.to_datetime(start_date)) &
    (cleaned_data["meeting_date"] <= pd.to_datetime(end_date))
].copy()

future_meetings = cleaned_data[
    (cleaned_data["normalized_committee_name"] == normalized_committee) &
    (cleaned_data["meeting_date"] > today)
].copy()

# Use normalized committee name for display consistency in filtering and outputs
display_committee_name = normalized_committee

if not past_meetings.empty:
    agenda_data = past_meetings.explode("agenda_items").dropna(subset=["agenda_items"])
    if not agenda_data.empty:
        agenda_flat = pd.json_normalize(agenda_data["agenda_items"])
        agenda_flat["meeting_date"] = agenda_data["meeting_date"].values
        agenda_flat["item_title"] = agenda_flat.get("item_title", "")
        agenda_flat["num_pdfs"] = agenda_flat["pdf_urls"].apply(lambda x: len(x) if isinstance(x, list) else 0)

        # Filter by search keyword if provided
        if search_keyword:
            agenda_flat = agenda_flat[
                agenda_flat["item_title"].str.contains(search_keyword, case=False, na=False)
            ]

        # Format meeting_date
        # Parse meeting_date as datetime, sort, then format
        agenda_flat["meeting_date"] = pd.to_datetime(agenda_flat["meeting_date"], errors="coerce")
        agenda_flat = agenda_flat.sort_values("meeting_date", ascending=False)
        agenda_flat["meeting_date"] = agenda_flat["meeting_date"].dt.strftime("%-d %b, %Y")

        # Rename columns
        display_cols = {
            "meeting_date": "Meeting Date",
            "item_title": "Item Title",
            "num_pdfs": "Number of Documents"
        }
        formatted_df = agenda_flat[list(display_cols.keys())].rename(columns=display_cols)

        # Set font style and wrapping for dataframe display
        st.markdown(
            """
            <style>
            .stDataFrame table {
                font-family: 'sans-serif';
                font-size: 0.875rem;
                white-space: normal;
                word-wrap: break-word;
            }
            .stDataFrame tbody tr td {
                white-space: normal !important;
                word-break: break-word !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # Display table without index
        st.dataframe(
            formatted_df,
            height=600,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No agenda items found for this committee in the past 12 months.")
else:
    st.info("No recent agenda items found for this committee.")

# Placeholder: Key Decisions
st.markdown("### Key Decisions from the Last 12 Months")
st.markdown("""
- Approved the 2025-2026 Budget [🔗](#)
- Adopted the new Local Transport Plan [🔗](#)
- Endorsed a revised Waste Management Strategy [🔗](#)
""")

# Display future agenda items
st.markdown("### Upcoming Agenda Items")

if not future_meetings.empty:
    future_agenda = future_meetings.explode("agenda_items").dropna(subset=["agenda_items"])
    future_flat = pd.json_normalize(future_agenda["agenda_items"])
    future_flat["meeting_date"] = future_agenda["meeting_date"].values
    future_flat["item_title"] = future_flat.get("item_title", "")
    future_flat["meeting_date"] = pd.to_datetime(future_flat["meeting_date"], errors="coerce")
    future_flat = future_flat.sort_values("meeting_date")

    future_flat["meeting_date"] = future_flat["meeting_date"].dt.strftime("%-d %b, %Y")

    st.markdown("")

    bullets = []
    for i, row in future_agenda.iterrows():
        meeting_date = pd.to_datetime(row["meeting_date"]).strftime("%-d %b, %Y")
        item_title = row["agenda_items"].get("item_title", "").strip()
        meeting_code = row.get("web_meeting_code")
        if item_title and meeting_code:
            url = f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={meeting_code}"
            bullets.append(f"- **{meeting_date}** – [{item_title}]({url})")

    st.markdown("\n".join(bullets))
else:
    st.info("No upcoming agenda items scheduled.")


# Placeholder: Committee-specific search
st.markdown("### Search These Committee Documents")
st.markdown(
    """
    <div style='padding: 1rem; border: 1px solid #ccc; border-radius: 8px; background-color: #f9f9f9; font-size: 0.95rem;'>
    🔍 This will soon allow you to search meeting minutes, agenda items, and documents for <strong>only this committee</strong>.
    </div>
    """,
    unsafe_allow_html=True
)

# Placeholder: Committee Members
st.markdown("### Current Committee Members")
st.markdown("""
- **Cllr Jane Smith** – Chair [🔗](#)
- **Cllr Mark Johnson** – Vice-Chair [🔗](#)
- **Cllr Aisha Khan** – Member [🔗](#)
- **Cllr David Lee** – Member [🔗](#)
""")
