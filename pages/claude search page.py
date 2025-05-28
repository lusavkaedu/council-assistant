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

# --------------------------
# 1. CONFIGURATION
# --------------------------
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
        border-left: 4px solid #d32f2f;
        background-color: #fafafa;
    }
    .filter-section {
        background-color: #fff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e9ecef;
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

# Sidebar filters
with st.sidebar:
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.markdown("### Search Filters")
    
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

# --------------------------
# 4. HEADER & DATA LOADING
# --------------------------
st.markdown("""
<div class="main-header">
    <h1>Kent Council Records Search</h1>
    <p>Search through thousands of council meetings, agenda items, and documents</p>
</div>
""", unsafe_allow_html=True)

# Load data
with st.spinner("Loading council data..."):
    data = load_base_data(PATHS)
    search_metadata = load_search_metadata(PATHS)

# Validate data
if not validate_data_integrity(data):
    st.stop()

# --------------------------
# 5. SEARCH INTERFACE
# --------------------------
st.markdown('<div class="search-box">', unsafe_allow_html=True)
query = st.text_input(
    "Search all council records:",
    value=st.session_state.get("query", ""),
    placeholder="e.g., 'road closures in Kent', 'SEND schools new places', 'climate change initiatives'",
    key="main_search_input",
    help="Enter keywords related to topics you're interested in. The search will look through agenda items and document summaries."
)
st.markdown('</div>', unsafe_allow_html=True)

# Update session state
if query != st.session_state.get("query", ""):
    st.session_state.query = query

# --------------------------
# 6. SEARCH TABS
# --------------------------
if st.session_state.get("query"):
    tabs = st.tabs(["Previously Discussed", "Documents", "AI Analysis"])
    
    # TAB 1: AGENDA ITEMS
    with tabs[0]:
        st.markdown("### Council Meeting Discussions")
        
        # Results per page selector
        col1, col2 = st.columns([3, 1])
        with col2:
            results_per_page_agenda = st.selectbox(
                "Results per page:",
                options=[10, 25, 50, 100],
                index=1,  # Default to 25
                key="agenda_results_per_page"
            )
        
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
                        # Merge with meetings data
                        if not data["meetings"].empty:
                            meeting_cols = [col for col in ["meeting_id", "committee_name", "web_meeting_code"] 
                                          if col in data["meetings"].columns]
                            agenda_results = agenda_results.merge(
                                data["meetings"][meeting_cols],
                                on="meeting_id",
                                how="left"
                            )
                        
                        st.session_state.agenda_results = agenda_results
                        
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
                            
                            filtered_agendas = agenda_results.copy()
                            if selected_committee != "All committees":
                                filtered_agendas = filtered_agendas[filtered_agendas['committee_name'] == selected_committee]
                        else:
                            filtered_agendas = agenda_results.copy()

                        # Sort and display results
                        filtered_agendas = sort_results(filtered_agendas, st.session_state.filters['sort_method'])
                        formatted_agendas = format_agenda_results_enhanced(
                            filtered_agendas, 
                            data["meetings"],
                            data["agendas"]
                        )
                        display_results_with_pagination(formatted_agendas, results_per_page=results_per_page_agenda, key_prefix="agenda")
                        
                    else:
                        st.info("No matching agenda items found. Try different search terms or check other tabs.")
                else:
                    st.error("Could not load agenda search index or metadata")
            except Exception as e:
                st.error(f"Error searching agendas: {str(e)}")

    # TAB 2: PDF DOCUMENTS
    with tabs[1]:
        st.markdown("### Council Documents & Reports")
        
        # Results per page selector
        col1, col2 = st.columns([3, 1])
        with col2:
            results_per_page = st.selectbox(
                "Results per page:",
                options=[10, 25, 50, 100],
                index=1,  # Default to 25
                key="pdf_results_per_page"
            )
        
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
                        
                        # Filters
                        filter_col1, filter_col2 = st.columns(2)
                        
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

    # TAB 3: AI ANALYSIS
    with tabs[2]:
        st.markdown("### AI Analysis")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("This will analyze your search results and provide insights, key findings, and policy developments.")
        with col2:
            generate_summary = st.button("Generate Analysis", key="generate_ai_summary", type="primary")
        
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
                            
                            # Display analysis
                            st.markdown("### Analysis Results")
                            st.markdown("---")
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
    # Welcome message
    st.markdown("""
    ### Welcome to Kent Council Records Search
    
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

# Debug section
if st.checkbox("Show debug information"):
    with st.expander("Debug: Data Status"):
        st.write("**Documents loaded:**", len(data["documents"]) if not data["documents"].empty else "None")
        st.write("**Meetings loaded:**", len(data["meetings"]) if not data["meetings"].empty else "None")
        st.write("**Agendas loaded:**", len(data["agendas"]) if not data["agendas"].empty else "None")
        st.write("**Search metadata loaded:**", {k: len(v) for k, v in search_metadata.items()})
        
        if st.session_state.get("query"):
            st.write("**Current search:**", st.session_state.query)
            if 'agenda_results' in st.session_state:
                st.write("**Agenda results:**", len(st.session_state.agenda_results))
            if 'pdf_results' in st.session_state:
                st.write("**PDF results:**", len(st.session_state.pdf_results))
                
                # Debug PDF URLs
                if st.checkbox("Debug PDF URLs"):
                    st.write("**Sample PDF result data:**")
                    pdf_sample = st.session_state.pdf_results.head(3)
                    for idx, row in pdf_sample.iterrows():
                        st.write(f"Row {idx}:")
                        st.write(f"  - doc_id: {row.get('doc_id')}")
                        st.write(f"  - url from search results: {row.get('url')}")
                        
                        # Check what's in the documents DataFrame
                        if not data["documents"].empty and 'doc_id' in row:
                            doc_match = data["documents"][data["documents"]['doc_id'] == row['doc_id']]
                            if not doc_match.empty:
                                st.write(f"  - url from documents df: {doc_match.iloc[0].get('url')}")
                                st.write(f"  - display_title: {doc_match.iloc[0].get('display_title')}")
                                st.write(f"  - source_filename: {doc_match.iloc[0].get('source_filename')}")
                            else:
                                st.write("  - No matching document found in documents df")
                        st.write("---")
                
                # Test direct URL links
                if st.checkbox("Test URL Links"):
                    st.write("**Direct URL Testing:**")
                    if 'pdf_results' in st.session_state and not st.session_state.pdf_results.empty:
                        test_row = st.session_state.pdf_results.iloc[0]
                        test_url = test_row.get('url')
                        test_title = test_row.get('display_title', 'Test Document')
                        
                        if pd.notna(test_url) and test_url:
                            # Original URL
                            st.write(f"**Original URL:** {test_url}")
                            
                            # URL encoded
                            encoded_url = str(test_url).strip().replace(' ', '%20').replace('(', '%28').replace(')', '%29')
                            st.write(f"**Encoded URL:** {encoded_url}")
                            
                            # Test different link formats
                            st.markdown(f"**Test Link 1 (original):** [Click here]({test_url})")
                            st.markdown(f"**Test Link 2 (encoded):** [Click here]({encoded_url})")
                            st.markdown(f"**Test Link 3 (HTML):** <a href='{encoded_url}' target='_blank'>Click here</a>", unsafe_allow_html=True)
                            
                            # Show exactly what HTML we're generating in the table
                            generated_html = f'<a href="{encoded_url}" target="_blank" style="color: #2c3e50; text-decoration: none; font-weight: 600; font-size: 16px;">{test_title}</a>'
                            st.write(f"**Generated HTML:** {generated_html}")
                            st.markdown(f"**Test Generated HTML:** {generated_html}", unsafe_allow_html=True)
                            
                            # Test the exact URL encoding that's being used in the function
                            if test_url:
                                url_parts = test_url.split('/')
                                if len(url_parts) > 1:
                                    from urllib.parse import quote
                                    url_parts[-1] = quote(url_parts[-1], safe=':/?#[]@!                            # Show exactly what HTML we're generating in the table
                            generated_html = f'<a href="{encoded_url}" target="_blank" style="color: #2c3e50; text-decoration: none; font-weight: 600; font-size: 16px;">{test_title}</a>'
                            st.write(f"**Generated HTML:** {generated_html}")
                            st.markdown(f"**Test Generated HTML:** {generated_html}", unsafe_allow_html=True)
                        else:
                            st.write("No URL found in first result")\'()*+,;=')
                                    function_encoded_url = '/'.join(url_parts)
                                else:
                                    function_encoded_url = quote(test_url, safe=':/?#[]@!                            # Show exactly what HTML we're generating in the table
                            generated_html = f'<a href="{encoded_url}" target="_blank" style="color: #2c3e50; text-decoration: none; font-weight: 600; font-size: 16px;">{test_title}</a>'
                            st.write(f"**Generated HTML:** {generated_html}")
                            st.markdown(f"**Test Generated HTML:** {generated_html}", unsafe_allow_html=True)
                        else:
                            st.write("No URL found in first result")\'()*+,;=')
                                
                                st.write(f"**Function-encoded URL:** {function_encoded_url}")
                                st.markdown(f"**Test Function-encoded:** [Click here]({function_encoded_url})")
                        else:
                            st.write("No URL found in first result")