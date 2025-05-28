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
            return pd.DataFrame(list(reader))  # Convert to list first
            
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
# 4. EMBEDDING GENERATION
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
# 5. SEARCH SERVICE SETUP
# --------------------------
@st.cache_resource
def load_search_index(index_path):
    """Load FAISS index with error handling"""
    try:
        if not Path(index_path).exists():
            st.error(f"Missing index file: {index_path}")
            return None
        return faiss.read_index(str(index_path))
    except Exception as e:
        st.error(f"Failed to load search index: {str(e)}")
        return None

# --------------------------
# 6. SEARCH FUNCTIONS
# --------------------------
def search_agendas(query, client, index, metadata_df, k=5):
    """Search agenda items using FAISS"""
    if index is None or metadata_df.empty:
        return pd.DataFrame()
        
    embedding = get_embedding(query, client)
    if embedding is None:
        return pd.DataFrame()
    
    # FAISS search
    distances, indices = index.search(embedding, k)
    
    # Prepare results
    valid_indices = indices[0][indices[0] < len(metadata_df)]  # Filter valid indices
    if len(valid_indices) == 0:
        return pd.DataFrame()
        
    results = metadata_df.iloc[valid_indices].copy()
    results["score"] = distances[0][:len(valid_indices)]
    return results.sort_values("score")

def search_pdfs(query, client, index, metadata_df, k=5):
    """Search PDF documents using FAISS"""
    if index is None or metadata_df.empty:
        return pd.DataFrame()
        
    embedding = get_embedding(query, client)
    if embedding is None:
        return pd.DataFrame()
    
    # FAISS search
    distances, indices = index.search(embedding, k)
    
    # Prepare results
    valid_indices = indices[0][indices[0] < len(metadata_df)]  # Filter valid indices
    if len(valid_indices) == 0:
        return pd.DataFrame()
        
    results = metadata_df.iloc[valid_indices].copy()
    results["score"] = distances[0][:len(valid_indices)]
    return results.sort_values("score")

# --------------------------
# 7. RESULT FORMATTERS
# --------------------------
def format_agenda_results(results, meetings_df, agendas_df):
    """Format agenda results with proper titles"""
    if results.empty:
        return pd.DataFrame()
    
    try:
        # Merge with meetings data first
        if not meetings_df.empty and "meeting_id" in results.columns:
            results = results.merge(
                meetings_df[["meeting_id", "web_meeting_code"]],
                on="meeting_id",
                how="left"
            )
        
        # Then merge with agendas to get titles
        if not agendas_df.empty:
            chunk_col = "chunk_id" if "chunk_id" in results.columns else "agenda_id"
            if chunk_col in results.columns:
                results = results.merge(
                    agendas_df[["agenda_id", "item_title"]],
                    left_on=chunk_col,
                    right_on="agenda_id",
                    how="left"
                )
        
        # Handle missing titles
        results["item_title"] = results.get("item_title", "Untitled Agenda Item").fillna("Untitled Agenda Item")
        
        # Date formatting with error handling
        if "meeting_date" in results.columns:
            try:
                results["Date"] = pd.to_datetime(
                    results["meeting_date"],
                    unit="ms",
                    errors="coerce"
                ).dt.strftime("%d %b %Y")
            except:
                results["Date"] = "Unknown Date"
        else:
            results["Date"] = "Unknown Date"
        
        # Create clickable dates
        if "web_meeting_code" in results.columns:
            results["Date"] = results.apply(
                lambda row: (
                    f'<a href="https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row["web_meeting_code"]}" '
                    f'target="_blank">{row["Date"]}</a>'
                    if pd.notna(row.get("web_meeting_code"))
                    else row["Date"]
                ),
                axis=1
            )
        
        # Clean committee names
        if "committee_id" in results.columns:
            results["Committee"] = (
                results["committee_id"]
                .str.replace("-", " ")
                .str.title()
            )
        elif "committee_name" in results.columns:
            results["Committee"] = results["committee_name"]
        else:
            results["Committee"] = "Unknown Committee"
        
        return results[[
            "Date",
            "Committee", 
            "item_title",
            "score"
        ]].rename(columns={
            "item_title": "Agenda Title",
            "score": "Score"
        })
        
    except Exception as e:
        st.error(f"Error formatting agenda results: {str(e)}")
        return pd.DataFrame()

def format_pdf_results(results, documents_df, meetings_df):
    """Robust PDF formatting with all possible fallbacks"""
    if results.empty:
        return pd.DataFrame()
    
    try:
        # Merge with documents data
        if not documents_df.empty and "doc_id" in results.columns:
            available_doc_cols = [col for col in ['doc_id', 'url', 'display_title', 'source_filename', 
                                'meeting_date', 'summary', 'committee_id', 'doc_category', 'meeting_id'] 
                                if col in documents_df.columns]
            
            results = results.merge(
                documents_df[available_doc_cols],
                on='doc_id',
                how='left'
            )
        
        # Try to get committee names
        if not meetings_df.empty and 'meeting_id' in results.columns and 'meeting_id' in meetings_df.columns:
            results = results.merge(
                meetings_df[['meeting_id', 'committee_name']],
                on='meeting_id',
                how='left'
            )
        
        # Committee name fallbacks
        if 'committee_name' not in results.columns or results['committee_name'].isna().all():
            if 'committee_id' in results.columns:
                results['committee_name'] = results['committee_id'].str.replace("-", " ").str.title()
            else:
                results['committee_name'] = 'Unknown Committee'
        
        # Document links with fallbacks
        results["Document"] = results.apply(
            lambda row: (
                f'<a href="{row["url"]}" target="_blank">'
                f'{row.get("display_title", row.get("source_filename", "Document"))}'
                f'</a>'
            ) if pd.notna(row.get("url")) else row.get("display_title", row.get("source_filename", "Document")),
            axis=1
        )
        
        # Date formatting with fallback
        if "meeting_date" in results.columns:
            try:
                results["Date"] = pd.to_datetime(
                    results["meeting_date"],
                    unit="ms",
                    errors="coerce"
                ).dt.strftime("%d %b %Y")
            except:
                results["Date"] = "Unknown Date"
        else:
            results["Date"] = "Unknown Date"
        
        # Type handling with fallbacks
        if "doc_category" in results.columns:
            type_mapping = {
                "prod": "Report",
                "eqia": "Impact Assessment", 
                "other": "Document",
                "minutes": "Minutes"
            }
            results["Type"] = results["doc_category"].apply(
                lambda x: type_mapping.get(str(x).lower(), str(x).title())
            )
        else:
            results["Type"] = "Document"
        
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
        
    except Exception as e:
        st.error(f"Error formatting PDF results: {str(e)}")
        return pd.DataFrame()

# --------------------------
# 8. AI SUMMARY FUNCTIONS
# --------------------------
def build_ai_prompt(query: str, agenda_results: pd.DataFrame, pdf_results: pd.DataFrame, 
                   agendas_df: pd.DataFrame, meetings_df: pd.DataFrame, documents_df: pd.DataFrame) -> str:
    """Builds complete AI prompt with all metadata"""
    context = ""
    
    # Add agenda items context
    if not agenda_results.empty:
        context += "## Relevant Agenda Items:\n"
        for _, row in agenda_results.head(4).iterrows():
            agenda_id = row.get('agenda_id', row.get('chunk_id', ''))
            
            # Get agenda text and meeting info
            agenda_text = ""
            meeting_info = {}
            
            if agenda_id and not agendas_df.empty:
                matching_agenda = agendas_df[agendas_df['agenda_id'] == agenda_id]
                if not matching_agenda.empty:
                    agenda_text = matching_agenda.iloc[0].get('item_text', '')
            
            meeting_id = row.get('meeting_id')
            if meeting_id and not meetings_df.empty:
                matching_meeting = meetings_df[meetings_df['meeting_id'] == meeting_id]
                if not matching_meeting.empty:
                    meeting_row = matching_meeting.iloc[0]
                    meeting_info = {
                        'date': meeting_row.get('meeting_date'),
                        'committee': meeting_row.get('committee_name'),
                        'title': meeting_row.get('meeting_title')
                    }
            
            # Format date
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
    
    # Add PDF documents context
    if not pdf_results.empty:
        context += "## Relevant Documents:\n"
        for _, row in pdf_results.head(6).iterrows():
            doc_id = row.get('doc_id')
            doc_meta = {}
            
            if doc_id and not documents_df.empty:
                matching_doc = documents_df[documents_df['doc_id'] == doc_id]
                if not matching_doc.empty:
                    doc_row = matching_doc.iloc[0]
                    doc_meta = {
                        'title': doc_row.get('display_title'),
                        'type': doc_row.get('doc_category'),
                        'date': doc_row.get('meeting_date'),
                        'committee': doc_row.get('committee_name'),
                        'summary': doc_row.get('summary')
                    }
            
            # Format date
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

# --------------------------
# 9. APP LAYOUT
# --------------------------
st.set_page_config(
    page_title="Council Records Search",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'query' not in st.session_state:
    st.session_state.query = ""
if 'filters' not in st.session_state:
    st.session_state.filters = {}

# Sidebar filters
with st.sidebar:
    st.markdown("### Search Filters")
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date",
            value=pd.to_datetime("today") - pd.Timedelta(days=365*2),
            format="DD-MM-YYYY"
        )
    with col2:
        end_date = st.date_input(
            "End date", 
            value=pd.to_datetime("today"),
            format="DD-MM-YYYY"
        )

    # Sorting options
    st.markdown("### Sorting Options")
    sort_method = st.selectbox(
        "Sort results by",
        options=["Relevance (default)", "Date (earliest first)", "Date (latest first)"],
        key="sort_method"
    )

    # Store filters in session state
    st.session_state.filters = {
        'start_date': start_date,
        'end_date': end_date,
        'sort_method': sort_method
    }

# Load data with progress bar
with st.spinner("Loading council data..."):
    data = load_base_data()

# Show data status
if not all(not df.empty for df in data.values()):
    st.error("❌ Critical data failed to load. Check file paths.")
    st.stop()

# Main search interface
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


# --------------------------
# Sort helper function
# --------------------------
def sort_results(results_df: pd.DataFrame, sort_method: str) -> pd.DataFrame:
    """Sort search results based on user preference"""
    if results_df.empty:
        return results_df

    if sort_method == "Date (earliest first)":
        if "meeting_date" in results_df.columns:
            return results_df.sort_values("meeting_date", ascending=True)
        elif "Date" in results_df.columns:
            return results_df.sort_values("Date", ascending=True)
    elif sort_method == "Date (latest first)":
        if "meeting_date" in results_df.columns:
            return results_df.sort_values("meeting_date", ascending=False)
        elif "Date" in results_df.columns:
            return results_df.sort_values("Date", ascending=False)

    if "score" in results_df.columns:
        return results_df.sort_values("score", ascending=True)

    return results_df

tabs = st.tabs(["Agenda Items", "PDF Documents", "AI Summary"])

# --------------------------
# TAB 1: AGENDA ITEMS
# --------------------------
with tabs[0]:
    if st.session_state.get("query"):
        with st.spinner(f"Searching agendas for '{st.session_state.query}'..."):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                agenda_index = load_search_index(PATHS["agenda_index"])
                agenda_meta = load_jsonl_safe(PATHS["agenda_metadata"])
                
                if agenda_index and not agenda_meta.empty:
                    agenda_results = search_agendas(st.session_state.query, client, agenda_index, agenda_meta)
                    
                    if not agenda_results.empty:
                        # Merge with meetings data for committee info
                        if not data["meetings"].empty:
                            agenda_results = agenda_results.merge(
                                data["meetings"][["meeting_id", "committee_name"]],
                                on="meeting_id",
                                how="left"
                            )
                        
                        st.session_state.agenda_results = agenda_results
                        
                        # Committee filter
                        available_committees = []
                        if 'committee_name' in agenda_results.columns:
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

                        # Sort results
                        filtered_agendas = sort_results(filtered_agendas, st.session_state.filters['sort_method'])

                        # Display results
                        formatted_agendas = format_agenda_results(
                            filtered_agendas, 
                            data["meetings"],
                            data["agendas"]
                        )
                        
                        if not formatted_agendas.empty:
                            st.markdown(
                                formatted_agendas.to_html(escape=False, index=False),
                                unsafe_allow_html=True
                            )
                        else:
                            st.warning("No results after filtering")
                    else:
                        st.warning("No matching agenda items found")
                else:
                    st.error("Could not load agenda search index or metadata")
            except Exception as e:
                st.error(f"Error searching agendas: {str(e)}")

# --------------------------
# TAB 2: PDF DOCUMENTS
# --------------------------
with tabs[1]:
    if st.session_state.get("query"):
        with st.spinner(f"Searching PDFs for '{st.session_state.query}'..."):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                pdf_index = load_search_index(PATHS["pdf_index"])
                pdf_meta = load_jsonl_safe(PATHS["pdf_metadata"])
                
                if pdf_index and not pdf_meta.empty:
                    pdf_results = search_pdfs(st.session_state.query, client, pdf_index, pdf_meta)
                    
                    if not pdf_results.empty:
                        # Merge with documents data
                        if not data["documents"].empty:
                            doc_cols = [col for col in ['doc_id', 'committee_id', 'doc_category', 'meeting_id'] 
                                      if col in data["documents"].columns]
                            pdf_results = pdf_results.merge(
                                data["documents"][doc_cols],
                                on='doc_id',
                                how='left'
                            )
                        
                        # Try merging with meetings
                        if not data["meetings"].empty and 'meeting_id' in pdf_results.columns:
                            pdf_results = pdf_results.merge(
                                data["meetings"][['meeting_id', 'committee_name']],
                                on='meeting_id',
                                how='left'
                            )
                        
                        st.session_state.pdf_results = pdf_results
                        
                        # Filters
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

                        # Sort results
                        filtered_pdfs = sort_results(filtered_pdfs, st.session_state.filters['sort_method'])

                        # Display results
                        formatted_pdfs = format_pdf_results(filtered_pdfs, data["documents"], data["meetings"])
                        if not formatted_pdfs.empty:
                            st.markdown(
                                formatted_pdfs.to_html(escape=False, index=False),
                                unsafe_allow_html=True
                            )
                        else:
                            st.warning("No results after filtering")
                    else:
                        st.warning("No matching PDF documents found")
                else:
                    st.error("Could not load PDF search index or metadata")
            except Exception as e:
                st.error(f"Error searching PDFs: {str(e)}")

# --------------------------
# TAB 3: AI SUMMARY
# --------------------------
with tabs[2]:
    st.markdown("""
    ## Council Records Analysis  
    Get an AI-powered summary of search results.
    """)
    
    if st.button("Generate Summary", key="generate_ai_summary"):
        if not st.session_state.get("query"):
            st.warning("Please perform a search first")
        elif 'agenda_results' not in st.session_state and 'pdf_results' not in st.session_state:
            st.warning("No search results available - please perform a search first")
        else:
            try:
                agenda_results = st.session_state.get("agenda_results", pd.DataFrame())
                pdf_results = st.session_state.get("pdf_results", pd.DataFrame())
                
                if agenda_results.empty and pdf_results.empty:
                    st.warning("No search results to summarize")
                else:
                    with st.spinner("Generating AI summary..."):
                        prompt = build_ai_prompt(
                            query=st.session_state.query,
                            agenda_results=agenda_results,
                            pdf_results=pdf_results,
                            agendas_df=data["agendas"],
                            meetings_df=data["meetings"],
                            documents_df=data["documents"]
                        )
                        
                        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                        response = client.chat.completions.create(
                            model=GPT_MODEL,
                            messages=[
                                {"role": "system", "content": "You're a council policy analyst."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3
                        )
                        
                        st.markdown(response.choices[0].message.content)
                        
                        with st.expander("View search context sent to AI"):
                            st.text(prompt)
            except Exception as e:
                st.error(f"Error generating AI summary: {str(e)}")

# Debug section (optional)
if st.checkbox("Show debug info"):
    with st.expander("Debug: Data Samples"):
        st.write("Documents sample:", data["documents"].head(1) if not data["documents"].empty else "Empty")
        st.write("Meetings sample:", data["meetings"].head(1) if not data["meetings"].empty else "Empty")
        st.write("Agendas sample:", data["agendas"].head(1) if not data["agendas"].empty else "Empty")