# Streamlined council search page using modular components
import streamlit as st
import pandas as pd
from pathlib import Path
import os
from openai import OpenAI
from dotenv import load_dotenv

# Import our custom modules
from modules.search.semantic_search import search_agendas, search_pdfs, sort_results, load_search_index
from modules.search.result_formatters import format_agenda_results_enhanced, format_pdf_results_enhanced, display_results_with_pagination
from modules.search.ai_analysis import generate_ai_analysis, get_analysis_source_info
from modules.data.loaders import load_base_data, load_search_metadata, validate_data_integrity
from modules.utils.logging_system import log_search, log_error, log_performance

# --------------------------
# 1. CONFIGURATION
# --------------------------
# Handle both local and cloud deployment paths
import os
if os.getenv("STREAMLIT_SHARING") or os.getenv("STREAMLIT_CLOUD") or not Path("/Users/lgfolder/github/council-assistant").exists():
    # Cloud deployment - use relative paths
    ROOT_FOLDER = Path(".")
    DATA_FOLDER = ROOT_FOLDER / "data"
else:
    # Local development - use absolute path
    ROOT_FOLDER = Path("/Users/lgfolder/github/council-assistant")
    DATA_FOLDER = ROOT_FOLDER / "data"

PATHS = {
    "meetings": DATA_FOLDER / "metadata/meetings.jsonl",
    "agendas": DATA_FOLDER / "metadata/agendas.jsonl",
    "pdf_warehouse": DATA_FOLDER / "metadata/pdf_warehouse.jsonl",
    "pdf_index": DATA_FOLDER / "embeddings/pdf_summaries/pdf_summary_index.faiss",
    "pdf_metadata": DATA_FOLDER / "embeddings/pdf_summaries/metadata_pdf_summaries.jsonl",
    "agenda_index": DATA_FOLDER / "embeddings/agendas/agenda_index.faiss",
    "agenda_metadata": DATA_FOLDER / "embeddings/agendas/metadata_agenda.jsonl"
}

GPT_MODEL = "gpt-4o-mini"
load_dotenv()

# --------------------------
# 2. PAGE CONFIGURATION
# --------------------------
st.set_page_config(
    page_title="Council Records Search",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply main styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
        padding: 1rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }
    .search-box {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        background-color: #fafafa;
    }
    .filter-section {
        background-color: #fff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    /* Make tabs more prominent */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 12px 24px;
        background-color: #f8f9fa;
        border-radius: 8px;
        border: 2px solid #dee2e6;
        font-size: 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d32f2f;
        color: white;
        border-color: #d32f2f;
    }
    /* Reduce heading size to balance with tabs */
    .stTabs + div h3 {
        font-size: 1.3rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------
# 3. SESSION STATE & SIDEBAR
# --------------------------
if 'query' not in st.session_state:
    st.session_state.query = ""
if 'filters' not in st.session_state:
    st.session_state.filters = {}

# Note: Sidebar will be rendered AFTER query processing

# --------------------------
# 4. HEADER & DATA LOADING
# --------------------------
st.markdown("""
<div class="main-header">
    <h1>Kent County Council Records Search</h1>
    <p>Search through thousands of council meetings, agenda items, and documents</p>
</div>
""", unsafe_allow_html=True)

# Load data
with st.spinner("Loading council data..."):
    data = load_base_data(PATHS)
    search_metadata = load_search_metadata(PATHS)

git config pull.rebase false# Validate data
if not validate_data_integrity(data):
    st.stop()

# --------------------------
# 5. SEARCH INTERFACE
# --------------------------
# Alternative approach: Let the widget manage its own state
query = st.text_input(
    "Search all council records:",
    placeholder="e.g., 'Why road closures in Kent are so frequent?', 'SEND schools new places', 'DEI initiatives'",
    key="search_input_direct",
    help="Enter keywords related to topics you're interested in. The search will look through agenda items and document summaries."
)

# Only update session state if the query actually changed and has content
if query and query.strip():
    # Check if this is actually a new search
    if query.strip() != st.session_state.get("query", ""):
        st.session_state.query = query.strip()
        # Clear previous results when new search is performed
        for key in ['agenda_results', 'pdf_results']:
            if key in st.session_state:
                del st.session_state[key]
elif not query:
    # Handle empty input
    if st.session_state.get("query", ""):
        st.session_state.query = ""
        for key in ['agenda_results', 'pdf_results']:
            if key in st.session_state:
                del st.session_state[key]
else:
    # If query exists but is just whitespace, keep the current session state query
    pass

# --------------------------
# 6. SIDEBAR FILTERS (AFTER QUERY PROCESSING)
# --------------------------
# Sidebar filters - only show when there's a search query
with st.sidebar:
    if st.session_state.get("query"):  # Only show filters when user has searched
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        st.markdown("### Search Filters")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start date",
                value=None,  # No default value - user chooses
                format="DD-MM-YYYY",
                help="Leave empty to search all dates"
            )
        with col2:
            end_date = st.date_input(
                "End date", 
                value=pd.to_datetime("today"),  # Default to today
                format="DD-MM-YYYY",
                help="Leave empty to search all dates"
            )

        st.markdown("### Sorting Options")
        sort_method = st.selectbox(
            "Sort results by",
            options=["Relevance (default)", "Date (earliest first)", "Date (latest first)"],
            key="sort_method"
        )
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Store filters
        st.session_state.filters = {
            'start_date': start_date,
            'end_date': end_date,
            'sort_method': sort_method
        }
    else:
        # No search query yet - completely empty sidebar
        st.session_state.filters = {
            'start_date': None,
            'end_date': pd.to_datetime("today").date(),
            'sort_method': "Relevance (default)"
        }

# --------------------------
# 7. SEARCH TABS
# --------------------------
if st.session_state.get("query"):
    tabs = st.tabs(["Meeting Discussions", "Documents & Reports", "AI Summary"])
    
    # TAB 0: AGENDA ITEMS
    with tabs[0]:
        st.markdown("### Council Meeting Discussions")
        
        with st.spinner(f"Searching past discussions for '{st.session_state.query}'..."):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                agenda_index = load_search_index(PATHS["agenda_index"])
                
                if agenda_index is not None and not search_metadata["agenda_metadata"].empty:
                    agenda_results = search_agendas(
                        st.session_state.query, 
                        client, 
                        agenda_index, 
                        search_metadata["agenda_metadata"],
                        k=100  # Get more results from FAISS
                    )
                    
                    if not agenda_results.empty:
                        # IMPORTANT: Merge with meetings data to get web_meeting_code
                        if not data["meetings"].empty:
                            # Make sure we include web_meeting_code in the merge
                            meeting_cols = [col for col in ["meeting_id", "committee_name", "web_meeting_code"] 
                                          if col in data["meetings"].columns]
                            agenda_results = agenda_results.merge(
                                data["meetings"][meeting_cols],
                                on="meeting_id",
                                how="left"
                            )
                        
                        st.session_state.agenda_results = agenda_results
                       
                        # NOW show filters with populated data
                        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
                        
                        with filter_col1:
                            # Committee filter
                            available_committees = []
                            if 'committee_name' in agenda_results.columns:
                                available_committees = agenda_results['committee_name'].dropna().unique()
                            
                            if len(available_committees) > 0:
                                selected_committee = st.selectbox(
                                    "Filter by committee:",
                                    options=["All committees"] + sorted(available_committees),
                                    key="agenda_committee_filter"
                                )
                            else:
                                selected_committee = "All committees"
                                st.selectbox("Filter by committee:", ["All committees"], key="agenda_committee_filter_empty")
                        
                        with filter_col2:
                            # Placeholder for alignment
                            st.write("")
                        
                        with filter_col3:
                            results_per_page_agenda = st.selectbox(
                                "Results per page:",
                                options=[10, 25, 50, 100],
                                index=1,  # Default to 25
                                key="agenda_results_per_page"
                            )
                        
                        # Apply committee filter
                        filtered_agendas = agenda_results.copy()
                        if selected_committee != "All committees" and 'committee_name' in filtered_agendas.columns:
                            filtered_agendas = filtered_agendas[filtered_agendas['committee_name'] == selected_committee]

                        # Sort and display results
                        filtered_agendas = sort_results(filtered_agendas, st.session_state.filters['sort_method'])
                        
                        # Don't pass the original meetings DataFrame since we already merged
                        formatted_agendas = format_agenda_results_enhanced(
                            filtered_agendas, 
                            pd.DataFrame(),  # Empty DataFrame instead of data["meetings"]
                            data["agendas"]
                        )
                        display_results_with_pagination(formatted_agendas, results_per_page=results_per_page_agenda, key_prefix="agenda")
                        
                    else:
                        st.info("No matching agenda items found. Try different search terms or check other tabs.")
                else:
                    st.error("Could not load agenda search index or metadata")
            except Exception as e:
                st.error(f"Error searching agendas: {str(e)}")

    # TAB 1: PDF DOCUMENTS
    with tabs[1]:
        st.markdown("### Council Documents & Reports")
        
        with st.spinner(f"Searching documents for '{st.session_state.query}'..."):
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                pdf_index = load_search_index(PATHS["pdf_index"])
                
                if pdf_index is not None and not search_metadata["pdf_metadata"].empty:
                    # Get more results initially (up to 100)
                    pdf_results = search_pdfs(
                        st.session_state.query, 
                        client, 
                        pdf_index, 
                        search_metadata["pdf_metadata"],
                        k=100  # Get more results from FAISS
                    )
                    
                    if not pdf_results.empty:
                        # Merge with documents data - this is where the URLs are!
                        if not data["documents"].empty:
                            # Get all needed columns including URL
                            doc_cols = [col for col in ['doc_id', 'url', 'display_title', 'source_filename', 
                                      'meeting_date', 'summary', 'committee_id', 'doc_category', 'meeting_id'] 
                                      if col in data["documents"].columns]
                            
                            pdf_results = pdf_results.merge(
                                data["documents"][doc_cols],
                                on='doc_id',
                                how='left'
                            )
                        
                        # Merge with meetings for committee names and meeting codes
                        if not data["meetings"].empty and 'meeting_id' in pdf_results.columns:
                            meeting_cols = [col for col in ['meeting_id', 'committee_name', 'web_meeting_code'] 
                                          if col in data["meetings"].columns]
                            pdf_results = pdf_results.merge(
                                data["meetings"][meeting_cols],
                                on='meeting_id',
                                how='left'
                            )
                        
                        st.session_state.pdf_results = pdf_results
                        
                        # NOW show filters with populated data - all on same line
                        filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
                        
                        with filter_col1:
                            committee_options = ["All committees"]
                            if 'committee_name' in pdf_results.columns:
                                committee_options += sorted(pdf_results['committee_name'].dropna().unique())
                            
                            selected_committee = st.selectbox(
                                "Filter by committee:",
                                options=committee_options,
                                key="pdf_committee_filter"
                            )
                        
                        with filter_col2:
                            type_options = ["All document types"]
                            if 'doc_category' in pdf_results.columns:
                                unique_types = pdf_results['doc_category'].dropna().unique()
                                type_mapping = {
                                    "prod": "Reports",
                                    "eqia": "Impact Assessments",
                                    "minutes": "Minutes",
                                    "other": "Other Documents"
                                }
                                type_options += [type_mapping.get(t.lower(), t.title()) for t in sorted(unique_types)]
                            
                            selected_type = st.selectbox(
                                "Filter by document type:",
                                options=type_options,
                                key="pdf_type_filter"
                            )
                        
                        with filter_col3:
                            results_per_page = st.selectbox(
                                "Results per page:",
                                options=[10, 25, 50, 100],
                                index=1,  # Default to 25
                                key="pdf_results_per_page"
                            )
                        
                        # Apply filters
                        filtered_pdfs = pdf_results.copy()
                        
                        if selected_committee != "All committees" and 'committee_name' in filtered_pdfs.columns:
                            filtered_pdfs = filtered_pdfs[filtered_pdfs['committee_name'] == selected_committee]
                        
                        if selected_type != "All document types" and 'doc_category' in filtered_pdfs.columns:
                            reverse_mapping = {
                                "Reports": "prod",
                                "Impact Assessments": "eqia",
                                "Minutes": "minutes",
                                "Other Documents": "other"
                            }
                            actual_type = reverse_mapping.get(selected_type, selected_type.lower())
                            filtered_pdfs = filtered_pdfs[filtered_pdfs['doc_category'] == actual_type]

                        # Sort results
                        filtered_pdfs = sort_results(filtered_pdfs, st.session_state.filters['sort_method'])
                        formatted_pdfs = format_pdf_results_enhanced(filtered_pdfs, data["documents"], data["meetings"])
                        display_results_with_pagination(formatted_pdfs, results_per_page=results_per_page, key_prefix="pdf")
                        
                    else:
                        st.info("No matching documents found. Try different search terms or check other tabs.")
                else:
                    st.error("Could not load PDF search index or metadata")
            except Exception as e:
                st.error(f"Error searching PDFs: {str(e)}")

    # TAB 2: AI SUMMARY
    with tabs[2]:
        st.markdown("### AI Summary")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            generate_summary = st.button("Generate Summary", key="generate_ai_summary", type="primary")
        with col2:
            st.markdown("""
            <div style="background-color: white; padding: 0.8rem; border-radius: 6px; border: 1px solid #dee2e6;">
                This will analyze your search results and provide insights, key findings, and policy developments.
            </div>
            """, unsafe_allow_html=True)
        
        if generate_summary:
            if not st.session_state.get("query"):
                st.warning("Please perform a search first")
            elif 'agenda_results' not in st.session_state and 'pdf_results' not in st.session_state:
                st.warning("No search results available - please search in the other tabs first")
            else:
                try:
                    agenda_results = st.session_state.get("agenda_results", pd.DataFrame())
                    pdf_results = st.session_state.get("pdf_results", pd.DataFrame())
                    
                    if agenda_results.empty and pdf_results.empty:
                        st.warning("No search results to analyze")
                    else:
                        with st.spinner("Analyzing council records and generating insights..."):
                            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                            
                            analysis = generate_ai_analysis(
                                query=st.session_state.query,
                                agenda_results=agenda_results,
                                pdf_results=pdf_results,
                                agendas_df=data["agendas"],
                                meetings_df=data["meetings"],
                                documents_df=data["documents"],
                                client=client,
                                model=GPT_MODEL
                            )
                            
                            # Display analysis directly
                            st.markdown(analysis)
                            
                            # Show source information
                            source_info = get_analysis_source_info(agenda_results, pdf_results)
                            with st.expander("Sources used in this analysis"):
                                if source_info["agenda_count"] > 0:
                                    st.write(f"**Agenda items analyzed:** {source_info['agenda_count']}")
                                if source_info["pdf_count"] > 0:
                                    st.write(f"**Documents analyzed:** {source_info['pdf_count']}")
                                st.write(f"**Total sources:** {source_info['total_sources']}")
                                
                except Exception as e:
                    st.error(f"Error generating AI analysis: {str(e)}")

else:
    # Welcome message with dynamic statistics
    st.markdown("### Welcome to Kent County Council Records Search")
    
    # Calculate statistics from loaded data
    total_meetings = len(data["meetings"]) if not data["meetings"].empty else 0
    total_documents = len(data["documents"]) if not data["documents"].empty else 0
    total_agendas = len(data["agendas"]) if not data["agendas"].empty else 0
    
    # Calculate date range
    date_range_text = ""
    if not data["meetings"].empty and "meeting_date" in data["meetings"].columns:
        try:
            # Convert meeting dates (assuming they're in milliseconds)
            dates = pd.to_datetime(data["meetings"]["meeting_date"], unit="ms", errors="coerce").dropna()
            if not dates.empty:
                start_year = dates.min().year
                end_year = min(dates.max().year, 2025)  # Cap at current year
                if start_year == end_year:
                    date_range_text = f"from {start_year}"
                else:
                    date_range_text = f"spanning {start_year} to {end_year}"
        except:
            date_range_text = ""
    
    # Display statistics
    if total_meetings > 0 or total_documents > 0:
        st.markdown(f"""
        **Search through {total_meetings:,} council meetings and {total_documents:,} documents {date_range_text}**
        """)
    
    st.markdown("""
    **What you can search for:**
    - **Meeting discussions**: Find what councillors have said about specific topics
    - **Official documents**: Search through reports, assessments, and meeting minutes  
    - **AI analysis**: Get intelligent summaries of complex policy topics
    
    **Example searches:**
    - *"road closures and traffic management"*
    - *"SEND schools and special educational needs"*
    - *"climate change and carbon reduction"*
    - *"housing development and planning applications"*
    
    **Start by entering your search terms above**
    """)