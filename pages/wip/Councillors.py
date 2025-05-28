import streamlit as st
import pandas as pd

st.set_page_config(page_title="Elected Councillors 2025", layout="wide")
st.title("🗳️ Kent County Council - Elected Councillors 2025")

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("data/elections/kent_councillors_elected_2025.csv", index_col="Councillor")
    df = df.copy()
    # Abbreviation logic
    def abbreviate_party(p):
        return (
            "LIB" if p == "Liberal Democrat" else
            "LAB" if "Labour" in p else
            "REF" if p == "Reform UK" else
            "CON" if p == "Conservative" else
            "GREEN" if p == "Green Party" else
            "UKIP" if p == "UK Independence Party" else
            "IND" if "Independent" in p else p
        )
    df["Party Abbr"] = df["Latest Party"].apply(abbreviate_party)
    if "Past Parties" in df.columns:
        df["Past Parties"] = df["Past Parties"].apply(
            lambda txt: ", ".join(sorted({abbreviate_party(p.strip()) for p in txt.split(",") if p.strip()})) if isinstance(txt, str) else "")
    return df

df = load_data()

# Sidebar filter by party abbreviation
parties = sorted(df["Party Abbr"].unique())
party_options = ["All Parties"] + parties
selected_option = st.sidebar.selectbox("Filter by Party:", party_options, index=0)

if selected_option == "All Parties":
    filtered_df = df
else:
    filtered_df = df[df["Party Abbr"] == selected_option]

# Drop the full party name for display, and reorder columns to include abbreviation
display_df = filtered_df.drop(columns=["Latest Party"]).rename(columns={"Party Abbr": "Party"})
display_df = display_df[["Division", "Party"] + [col for col in display_df.columns if col not in ["Division", "Party"]]]

# Show full-width fixed table (not scrollable box)
#st.table(display_df, use_container_width=True)
st.table(display_df)
#st.dataframe(display_df, use_container_width=True, hide_index=False)