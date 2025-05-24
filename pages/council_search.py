# council_search.py
import streamlit as st
import pandas as pd
import jsonlines
from pathlib import Path
import os
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
from typing import List, Dict


# --------------------------
# 1. CONFIGURE PATHS (EXACT TO YOUR SYSTEM)
# --------------------------
ROOT_FOLDER = Path("/Users/lgfolder/github/council-assistant")
DATA_FOLDER = ROOT_FOLDER / "data"

PATHS = {
    "meetings": DATA_FOLDER / "metadata/meetings.jsonl",
    "agendas": DATA_FOLDER / "metadata/agendas.jsonl",
    "pdf_warehouse": DATA_FOLDER / "metadata/pdf_warehouse.jsonl",  # Primary source
    "pdf_index": DATA_FOLDER / "embeddings/pdf_summaries/pdf_summary_index.faiss",
    "pdf_metadata": DATA_FOLDER / "embeddings/pdf_summaries/metadata_pdf_summaries.jsonl",
    "agenda_index": DATA_FOLDER / "embeddings/agendas/agenda_index.faiss",
    "agenda_metadata": DATA_FOLDER / "embeddings/agendas/metadata_agenda.jsonl"
}

GPT_MODEL = "gpt-4o-mini"  # Consistent model for all AI interactions

load_dotenv()  # Load .env file for OpenAI API key

# --------------------------
# 2. SAFE DATA LOADER FUNCTION
# --------------------------
def load_jsonl_safe(filepath):
    """Loads a .jsonl file with error handling"""
    try:
        if not filepath.exists():
            st.error(f"Missing file: {filepath}")
            return pd.DataFrame()
        
        with jsonlines.open(filepath) as reader:
            return pd.DataFrame(reader)
            
    except Exception as e:
        st.error(f"Failed to load {filepath}: {str(e)}")
        return pd.DataFrame()

# --------------------------
# 3. INITIAL DATA LOAD
# --------------------------
@st.cache_data
def load_base_data():
    """Loads essential datasets using the new warehouse"""
    return {
        "documents": load_jsonl_safe(PATHS["pdf_warehouse"]),  # Single source of truth
        "meetings": load_jsonl_safe(PATHS["meetings"]),
        "agendas": load_jsonl_safe(PATHS["agendas"])
    }

# --------------------------
# 4. APP LAYOUT
# --------------------------
st.set_page_config(
    page_title="Council Records Search",
    layout="wide",
    initial_sidebar_state="expanded"
)
with st.sidebar:
    st.markdown("### Search Filters")
    
    # Date range filter (shared across tabs)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date",
            value=pd.to_datetime("today") - pd.Timedelta(days=365*5), # Default to 2 years ago   
            format="DD-MM-YYYY"
        )
    with col2:
        end_date = st.date_input(
            "End date", 
            value=pd.to_datetime("today"),
            format="DD-MM-YYYY"
        )
    
    # Store filters in session state
    st.session_state.filters = {
        'start_date': start_date,
        'end_date': end_date,
        'pdf_filters': {},
        'agenda_filters': {}
    }

# Load data with progress bar
with st.spinner("Loading council data..."):
    data = load_base_data()

# Show data status
if not all(not df.empty for df in data.values()):
    st.error("❌ Critical data failed to load. Check file paths.")
    st.stop()  # Halt the app if data is missing

#st.success(f"✅ Loaded: {', '.join([k for k,v in data.items() if not v.empty])}")


# --------------------------
# 2. SEARCH SERVICE SETUP
# --------------------------
@st.cache_resource
def load_search_index(index_path):
    """Load FAISS index with error handling"""
    try:
        return faiss.read_index(str(index_path))
    except Exception as e:
        st.error(f"Failed to load search index: {str(e)}")
        return None


# --------------------------
# 2. TAB-SPECIFIC FILTERS AND FILTERING LOGIC
# --------------------------
def filter_results(results, result_type="pdf"):
    """Apply filters to results based on type"""
    if results.empty:
        return results
    
    filtered = results.copy()
    
    # Convert meeting_date to datetime
    filtered['meeting_date'] = pd.to_datetime(filtered['meeting_date'], unit='ms')
    
    # Apply date filter
    filtered = filtered[
        (filtered['meeting_date'].dt.date >= st.session_state.filters['start_date']) &
        (filtered['meeting_date'].dt.date <= st.session_state.filters['end_date'])
    ]
    
    # Apply type-specific filters
    if result_type == "pdf" and 'pdf_filters' in st.session_state.filters:
        filters = st.session_state.filters['pdf_filters']
        if 'committee' in filters:
            filtered = filtered[filtered['committee_name'] == filters['committee']]
        if 'doc_category' in filters:
            filtered = filtered[filtered['doc_category'] == filters['doc_category']]
    
    elif result_type == "agenda" and 'agenda_filters' in st.session_state.filters:
        filters = st.session_state.filters['agenda_filters']
        if 'committee' in filters:
            filtered = filtered[filtered['committee_id'] == filters['committee']]
    
    return filtered


# --------------------------
# 3. EMBEDDING GENERATION
# --------------------------
def get_embedding(query, client):
    """Generate embedding vector for search"""
    try:
        response = client.embeddings.create(
            input=[query],
            model="text-embedding-3-small"
        )
        return np.array(response.data[0].embedding, dtype=np.float32).reshape(1, -1)
    except Exception as e:
        st.error(f"Embedding failed: {str(e)}")
        return None

# --------------------------
# 4. SEARCH FUNCTIONALITY
# --------------------------
def search_agendas(query, client, index, metadata_df, k=5):
    """Search agenda items using FAISS"""
    embedding = get_embedding(query, client)
    if embedding is None:
        return pd.DataFrame()
    
    # FAISS search
    distances, indices = index.search(embedding, k)
    
    # Prepare results
    results = metadata_df.iloc[indices[0]].copy()
    results["score"] = distances[0]
    return results.sort_values("score")

def format_agenda_results(results, meetings_df, agendas_df):
    """Format agenda results with proper titles"""
    if results.empty:
        return pd.DataFrame()
    
    # 1. Merge with meetings data first
    results = results.merge(
        meetings_df[["meeting_id", "web_meeting_code"]],
        on="meeting_id",
        how="left"
    )
    
    # 2. Then merge with agendas to get titles
    results = results.merge(
        agendas_df[["agenda_id", "item_title"]],
        left_on="chunk_id",  # Assuming this matches agenda_id
        right_on="agenda_id",
        how="left"
    )
    
    # Handle missing titles
    results["item_title"] = results["item_title"].fillna("Untitled Agenda Item")
    
    # Date formatting
    results["Date"] = pd.to_datetime(
        results["meeting_date"],
        unit="ms"
    ).dt.strftime("%d %b %Y")
    
    # Create clickable dates
    results["Date"] = results.apply(
        lambda row: (
            f'<a href="https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row["web_meeting_code"]}" '
            f'target="_blank">{row["Date"]}</a>'
            if pd.notna(row["web_meeting_code"])
            else row["Date"]
        ),
        axis=1
    )
    
    # Clean committee names
    results["Committee"] = (
        results["committee_id"]
        .str.replace("-", " ")
        .str.title()
    )
    
    return results[[
        "Date",
        "Committee",
        "item_title",
        "score"
    ]].rename(columns={
        "item_title": "Agenda Title",
        "score": "Score"
    })


# --------------------------
# 2. PDF SEARCH FUNCTION
# --------------------------
def search_pdfs(query, client, index, metadata_df, k=5):
    """Search PDF documents using FAISS"""
    embedding = get_embedding(query, client)
    if embedding is None:
        return pd.DataFrame()
    
    # FAISS search
    distances, indices = index.search(embedding, k)
    
    # Prepare results
    results = metadata_df.iloc[indices[0]].copy()
    results["score"] = distances[0]
    return results.sort_values("score")

# --------------------------
# 3. PDF RESULT FORMATTER
# --------------------------

def format_pdf_results(results, documents_df, meetings_df):
    """Robust PDF formatting with all possible fallbacks"""
    if results.empty:
        return pd.DataFrame()
    
    # 1. First ensure we have basic columns
    required_doc_cols = ['doc_id', 'url', 'display_title', 'source_filename', 
                        'meeting_date', 'summary']
    available_doc_cols = [col for col in required_doc_cols if col in documents_df.columns]
    
    results = results.merge(
        documents_df[available_doc_cols + ['committee_id', 'doc_category']],
        on='doc_id',
        how='left'
    )
    
    # 2. Try to get committee names with multiple fallbacks
    if 'committee_id' in results.columns:
        # First try merging with meetings
        if 'meeting_id' in results.columns and 'meeting_id' in meetings_df.columns:
            meetings_cols = ['meeting_id', 'committee_name']
            results = results.merge(
                meetings_df[meetings_cols],
                on='meeting_id',
                how='left'
            )
        
        # Fallback to committee_id if name not found
        if 'committee_name' not in results.columns:
            results['committee_name'] = results['committee_id']
    
    # 3. Final fallback if no committee info at all
    if 'committee_name' not in results.columns:
        results['committee_name'] = 'Unknown Committee'
    
    # Document links with fallbacks
    results["Document"] = results.apply(
        lambda row: (
            f'<a href="{row["url"]}" target="_blank">'
            f'{row.get("display_title", row.get("source_filename", "Document"))}'
            f'</a>'
        ) if pd.notna(row.get("url")) else row.get("display_title", "Document"),
        axis=1
    )
    
    # Date formatting with fallback
    results["Date"] = pd.to_datetime(
        results["meeting_date"],
        unit="ms",
        errors="coerce"
    ).dt.strftime("%d %b %Y")
    
    # Type handling with fallbacks
    type_mapping = {
        "prod": "Report",
        "eqia": "Impact Assessment",
        "other": "Document",
        "minutes": "Minutes"
    }
    results["Type"] = results["doc_category"].apply(
        lambda x: type_mapping.get(str(x).lower(), str(x).title())
    ) if "doc_category" in results.columns else "Document"
    
    return results[[
        "Date",
        "committee_name", 
        "Document",
        "Type",
        "score"
    ]].rename(columns={
        "committee_name": "Committee",
        "score": "Score"
    })


# --------------------------
# 8. AI SUMMARY FUNCTIONS
# --------------------------

def build_ai_prompt(query: str, agenda_results: pd.DataFrame, pdf_results: pd.DataFrame, 
                   agendas_df: pd.DataFrame, meetings_df: pd.DataFrame, documents_df: pd.DataFrame) -> str:
    """Builds complete AI prompt with all metadata"""
    context = ""
    
    # 1. Add full agenda items (top 4) with complete metadata
    if not agenda_results.empty:
        context += "## Relevant Agenda Items:\n"
        for _, row in agenda_results.head(4).iterrows():
            # Get agenda ID from either column
            agenda_id = row.get('agenda_id', row.get('chunk_id', ''))
            
            # Find matching agenda text and metadata
            agenda_text = ""
            meeting_info = {}
            if agenda_id:
                # Get full agenda text
                matching_agenda = agendas_df[agendas_df['agenda_id'] == agenda_id]
                if not matching_agenda.empty:
                    agenda_text = matching_agenda.iloc[0].get('item_text', '')
                
                # Get meeting metadata
                meeting_id = row.get('meeting_id')
                if meeting_id:
                    matching_meeting = meetings_df[meetings_df['meeting_id'] == meeting_id]
                    if not matching_meeting.empty:
                        meeting_info = {
                            'date': matching_meeting.iloc[0].get('meeting_date'),
                            'committee': matching_meeting.iloc[0].get('committee_name'),
                            'title': matching_meeting.iloc[0].get('meeting_title')
                        }
            
            # Format date if available
            date_str = "Unknown date"
            if meeting_info.get('date'):
                try:
                    date_str = pd.to_datetime(meeting_info['date'], unit='ms').strftime('%d %b %Y')
                except:
                    pass
            
            context += f"### {row.get('item_title', 'Agenda Item')}\n"
            context += f"- Date: {date_str}\n"
            context += f"- Committee: {meeting_info.get('committee', 'Unknown committee')}\n"
            context += f"- Meeting: {meeting_info.get('title', '')}\n"
            context += f"\n**Content:**\n{agenda_text or 'No content available'}\n\n"
    
    # 2. Add PDF documents (top 6) with complete metadata
    if not pdf_results.empty:
        context += "## Relevant Documents:\n"
        for _, row in pdf_results.head(6).iterrows():
            # Get full document metadata
            doc_id = row.get('doc_id')
            doc_meta = {}
            if doc_id:
                matching_doc = documents_df[documents_df['doc_id'] == doc_id]
                if not matching_doc.empty:
                    doc_meta = {
                        'title': matching_doc.iloc[0].get('display_title'),
                        'type': matching_doc.iloc[0].get('doc_category'),
                        'date': matching_doc.iloc[0].get('meeting_date'),
                        'committee': matching_doc.iloc[0].get('committee_name'),
                        'summary': matching_doc.iloc[0].get('summary')
                    }
            
            # Format date if available
            date_str = "Unknown date"
            if doc_meta.get('date'):
                try:
                    date_str = pd.to_datetime(doc_meta['date'], unit='ms').strftime('%d %b %Y')
                except:
                    pass
            
            # Format type
            doc_type = str(doc_meta.get('type', '')).upper()
            type_mapping = {
                "PROD": "Report",
                "EQIA": "Impact Assessment"
            }
            doc_type = type_mapping.get(doc_type, doc_type)
            
            context += f"### {doc_meta.get('title', 'Document')}\n"
            context += f"- Type: {doc_type}\n"
            context += f"- Date: {date_str}\n"
            context += f"- Committee: {doc_meta.get('committee', 'Unknown committee')}\n"
            context += f"\n**Summary:**\n{doc_meta.get('summary', 'No summary available')}\n\n"
    
    return f"""Analyze these council records about '{query}'. Focus on:

1. Key policy positions and decisions
2. Timeline of changes/developments
3. Differences between committees
4. Specific actions taken or proposed

Context:
{context}

Guidelines:
- Reference documents by title and date
- Note conflicting viewpoints if present
- Highlight most recent developments
- Keep analysis under 400 words"""


def generate_ai_summary():
    """Handles all AI summary generation with consistent settings"""
    if not st.session_state.get("query"):
        st.warning("Please perform a search first")
        return
    if "agenda_results" not in st.session_state and "pdf_results" not in st.session_state:
        st.warning("No search results available - please perform a search first")
        return

    with st.spinner("Generating AI analysis..."):
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Build prompt
        prompt = build_ai_prompt(
            query=st.session_state.query,
            agenda_results=st.session_state.get("agenda_results", pd.DataFrame()),
            pdf_results=st.session_state.get("pdf_results", pd.DataFrame()),
            agendas_df=data["agendas"],
            meetings_df=data["meetings"],
            documents_df=data["documents"]
        )

        # Generate response with consistent model/settings
        response = client.chat.completions.create(
            model=GPT_MODEL,  
            messages=[
                {"role": "system", "content": "You're a UK council policy analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Consistent creativity level
        )
        
        # Store and display results
        st.session_state.last_ai_summary = response.choices[0].message.content
        return response.choices[0].message.content



# --------------------------
# MAIN APP LAYOUT
# --------------------------
st.title("🔍 Kent Council Records")
query = st.text_input(
    "Search all council records:",
    value=st.session_state.get("query", ""),
    placeholder="E.g.: 'Why do we have so many road closures in Kent?' or 'SEND schools new places'",
    key="main_search_input"
)

# Store query in session state
if query != st.session_state.get("query", ""):
    st.session_state.query = query
    st.session_state.search_run = False  # Reset search flag

tabs = st.tabs(["Agenda Items", "PDF Documents", "AI Summary"])


# --------------------------
# TAB 1: AGENDA ITEMS
# --------------------------

with tabs[0]:  # Agenda Items
    if st.session_state.get("query"):
        with st.spinner(f"Searching agendas for '{st.session_state.query}'..."):
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            agenda_index = load_search_index(PATHS["agenda_index"])
            agenda_meta = load_jsonl_safe(PATHS["agenda_metadata"])
            
            if agenda_index and not agenda_meta.empty:
                agenda_results = search_agendas(st.session_state.query, client, agenda_index, agenda_meta)
                
                # Merge with meetings data for committee info
                agenda_results = agenda_results.merge(
                    data["meetings"][["meeting_id", "committee_name"]],
                    on="meeting_id",
                    how="left"
                )
                
                st.session_state.agenda_results = agenda_results
                
                if not agenda_results.empty:
                    # Committee filter
                    available_committees = agenda_results['committee_name'].dropna().unique()
                    selected_committee = st.selectbox(
                        "Filter by committee",
                        options=["All"] + sorted(available_committees),
                        key="agenda_committee_filter"
                    )
                    
                    # Apply filter
                    filtered_agendas = agenda_results.copy()
                    if selected_committee != "All":
                        filtered_agendas = filtered_agendas[filtered_agendas['committee_name'] == selected_committee]
                    
                    # Display results
                    formatted_agendas = format_agenda_results(
                        filtered_agendas, 
                        data["meetings"],
                        data["agendas"]
                    )
                    st.markdown(
                        formatted_agendas.to_html(escape=False, index=False),
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("No matching agenda items found")

# --------------------------
# TAB 2: PDF DOCUMENTS
# --------------------------

with tabs[1]:
    if st.session_state.get("query"):
        with st.spinner(f"Searching PDFs for '{st.session_state.query}'..."):
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            pdf_index = load_search_index(PATHS["pdf_index"])
            pdf_meta = load_jsonl_safe(PATHS["pdf_metadata"])
            
            if pdf_index and not pdf_meta.empty:
                # Get initial results
                pdf_results = search_pdfs(st.session_state.query, client, pdf_index, pdf_meta)
                
                # First merge with documents
                doc_cols = ['doc_id', 'committee_id', 'doc_category']
                if 'meeting_id' in data["documents"].columns:
                    doc_cols.append('meeting_id')
                
                pdf_results = pdf_results.merge(
                    data["documents"][doc_cols],
                    on='doc_id',
                    how='left'
                )
                
                # Then try merging with meetings if possible
                if 'meeting_id' in pdf_results.columns and 'meeting_id' in data["meetings"].columns:
                    pdf_results = pdf_results.merge(
                        data["meetings"][['meeting_id', 'committee_name']],
                        on='meeting_id',
                        how='left'
                    )
                
                st.session_state.pdf_results = pdf_results
                
                if not pdf_results.empty:
                    # Prepare filters
                    filter_col1, filter_col2 = st.columns(2)
                    
                    with filter_col1:
                        committee_options = ["All"]
                        if 'committee_name' in pdf_results.columns:
                            committee_options += sorted(pdf_results['committee_name'].dropna().unique())
                        elif 'committee_id' in pdf_results.columns:
                            committee_options += sorted(pdf_results['committee_id'].dropna().unique())
                        
                        selected_committee = st.selectbox(
                            "Filter by committee",
                            options=committee_options,
                            key="pdf_committee_filter"
                        )
                    
                    with filter_col2:
                        type_options = ["All"]
                        if 'doc_category' in pdf_results.columns:
                            type_options += sorted(pdf_results['doc_category'].dropna().unique())
                        
                        selected_type = st.selectbox(
                            "Filter by document type",
                            options=type_options,
                            key="pdf_type_filter"
                        )
                    
                    # Apply filters
                    filtered_pdfs = pdf_results.copy()
                    if selected_committee != "All":
                        if 'committee_name' in filtered_pdfs.columns:
                            filtered_pdfs = filtered_pdfs[filtered_pdfs['committee_name'] == selected_committee]
                        elif 'committee_id' in filtered_pdfs.columns:
                            filtered_pdfs = filtered_pdfs[filtered_pdfs['committee_id'] == selected_committee]
                    
                    if selected_type != "All" and 'doc_category' in filtered_pdfs.columns:
                        filtered_pdfs = filtered_pdfs[filtered_pdfs['doc_category'] == selected_type]
                    
                    # Display results
                    formatted_pdfs = format_pdf_results(filtered_pdfs, data["documents"], data["meetings"])
                    st.markdown(
                        formatted_pdfs.to_html(escape=False, index=False),
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("No matching PDF documents found")
                    
# --------------------------
# TAB 3: AI SUMMARY
# --------------------------

with tabs[2]:
    st.markdown("""
    ## Council Records Analysis  
    Get an AI-powered summary of filtered documents.
    """)
    
    if st.button("Generate Summary"):
        # Get filtered results for AI analysis
        filtered_agendas = filter_results(
            st.session_state.get("agenda_results", pd.DataFrame()),
            "agenda"
        )
        filtered_pdfs = filter_results(
            st.session_state.get("pdf_results", pd.DataFrame()),
            "pdf"
        )
        
        if filtered_agendas.empty and filtered_pdfs.empty:
            st.warning("No matching documents after filtering")
        else:
            summary = generate_ai_summary(
                query=st.session_state.query,
                agenda_results=filtered_agendas,
                pdf_results=filtered_pdfs,
                # ... [other arguments] ...
            )
            st.markdown(summary)

# Temporary debug section
#with st.expander("Debug: Data Samples"):
#    st.write("Documents sample:", data["documents"].head(1))    
#    st.write("Meetings sample:", data["meetings"].head(1))
