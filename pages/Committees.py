import streamlit as st
st.set_page_config(page_title="Committees", layout="wide")
import json
from pathlib import Path

COMMITTEE_FILE = Path("data/references/committees.jsonl")

@st.cache_data
def load_committees():
    with open(COMMITTEE_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]

committees_data = load_committees()
available_committees = [c["name"] for c in committees_data]



# Dropdown for committee selection
selected_committee = st.selectbox("Select a committee", [""] + available_committees)

# Content only appears if a selection is made
if selected_committee:
    committee = next((c for c in committees_data if c["name"] == selected_committee), None)
    if committee:
        st.markdown(f"## {committee['name']}")

        # Committee Purpose
        st.markdown("### Committee Purpose")
        st.info(committee.get("description", "No description available."))

        # Placeholder: Key Decisions
        st.markdown("### Key Decisions from the Last 12 Months")
        st.markdown("""
        - Approved the 2025-2026 Budget [🔗](#)
        - Adopted the new Local Transport Plan [🔗](#)
        - Endorsed a revised Waste Management Strategy [🔗](#)
        """)

        # Placeholder: Upcoming Agenda Items
        st.markdown("### Upcoming Agenda Items")
        st.markdown("""
        - Review of Planning Policy for Renewable Energy Sites
        - Annual Performance Report – Adult Social Care
        - Adoption of New Standing Orders
        """)

        # Placeholder: Committee Members
        st.markdown("### Current Committee Members")
        st.markdown("""
        - **Cllr Jane Smith** – Chair [🔗](#)
        - **Cllr Mark Johnson** – Vice-Chair [🔗](#)
        - **Cllr Aisha Khan** – Member [🔗](#)
        - **Cllr David Lee** – Member [🔗](#)
        """)
