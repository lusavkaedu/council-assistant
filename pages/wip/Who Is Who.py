import streamlit as st
import pandas as pd
from pathlib import Path

# MUST be the first Streamlit command
st.set_page_config(layout="wide", page_title="Council Who's Who")

# Configuration
TABLES_PATH = Path("/Users/lgfolder/github/council-assistant/data/people/reference")

# Load tables with proper type conversion
@st.cache_data
def load_tables():
    tables = {
        'councillors': pd.read_csv(TABLES_PATH / "councillors.csv"),
        'civil_servants': pd.read_csv(TABLES_PATH / "civil_servants.csv"),
        'participation': pd.read_csv(TABLES_PATH / "participation.csv"),
        'ambiguities': pd.read_csv(TABLES_PATH / "ambiguities.csv")
    }
    
    # Special handling for divisions table which contains numeric data
    divisions = pd.read_csv(TABLES_PATH / "divisions.csv")
    tables['divisions'] = divisions.astype(str)  # Convert all to string for display
    return tables

# Main app function
def main():
    tables = load_tables()
    
    st.title("Council Who's Who Directory")
    
    # 1. Current Councillors
    st.header("Current Councillors")
    st.dataframe(
        tables['councillors'],
        column_config={
            "full_name": "Name",
            "division": "Division/Ward",
            "party": "Political Party"
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 2. Civil Servants
    st.header("Civil Servants Directory")
    st.dataframe(
        tables['civil_servants'],
        column_config={
            "formatted_name": "Name",
            "raw_name": "As Appears in Minutes"
        },
        hide_index=True,
        use_container_width=True
    )
    
    # 3. Participation Heatmap - Fixed parenthesis issue here
    st.header("Meeting Participation")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.dataframe(
            tables['participation'],
            column_config={
                "first_name": "First Name",
                "last_name": "Last Name",
                "position": "Role",
                "meetings_attended": st.column_config.ProgressColumn(
                    "Meetings Attended",
                    format="%d",
                    min_value=0,
                    max_value=int(tables['participation']['meetings_attended'].max())
                )
            },
            hide_index=True
        )
    with col2:
        st.metric(
            "Most Active Participant",
            value=tables['participation'].iloc[0]['first_name'] + " " + tables['participation'].iloc[0]['last_name'],
            delta=f"{int(tables['participation'].iloc[0]['meetings_attended'])} meetings"
        )
    
    # 4. Division Affiliations
    st.header("Division Affiliations")
    st.dataframe(
        tables['divisions'],
        use_container_width=True,
        column_config={
            col: st.column_config.TextColumn(col) for col in tables['divisions'].columns
        }
    )
    
    # 5. Ambiguities (if any)
    if not tables['ambiguities'].empty:
        st.header("Names Needing Review")
        st.write("These names matched multiple possible councillors:")
        st.dataframe(
            tables['ambiguities'],
            column_config={
                "raw_name": "Name in Minutes",
                "possible_matches": "Possible Matches"
            },
            hide_index=True
        )
    
    # Optional enhancements
    with st.expander("🔍 Search and Filter Options"):
        # Search functionality
        search_term = st.text_input("Search by name across all tables")
        if search_term:
            st.write("Matching councillors:")
            councillors_results = tables['councillors'][
                tables['councillors']['full_name'].str.contains(search_term, case=False)
            ]
            st.dataframe(councillors_results)
            
            st.write("Matching civil servants:")
            civil_servants_results = tables['civil_servants'][
                tables['civil_servants']['formatted_name'].str.contains(search_term, case=False)
            ]
            st.dataframe(civil_servants_results)

        # Division filter
        divisions = tables['councillors']['division'].unique()
        selected_division = st.selectbox("Filter councillors by division", ['All'] + sorted(list(divisions)))
        if selected_division != 'All':
            filtered = tables['councillors'][tables['councillors']['division'] == selected_division]
            st.dataframe(filtered)
    
    # Export buttons
    st.download_button(
        label="Download Councillors Data",
        data=tables['councillors'].to_csv(index=False).encode('utf-8'),
        file_name='councillors.csv',
        mime='text/csv'
    )

    st.download_button(
        label="Download Civil Servants Data",
        data=tables['civil_servants'].to_csv(index=False).encode('utf-8'),
        file_name='civil_servants.csv',
        mime='text/csv'
    )

# Run the app
if __name__ == "__main__":
    main()