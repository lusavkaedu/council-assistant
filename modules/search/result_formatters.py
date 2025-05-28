"""
Result formatting functions for displaying search results in enhanced UI
"""
import pandas as pd
import streamlit as st
from urllib.parse import quote

import re

def clean_agenda_text(text):
    """
    Improved text cleaning with selective line break preservation
    - Double line breaks (\n\n) become single breaks (paragraph separation)
    - Single line breaks (\n) become spaces (continuous text)
    - Preserves numbered lists and key sections
    - Handles addresses and references more carefully
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    cleaned = text
    
    # Step 1: Normalize different types of line breaks
    cleaned = cleaned.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\r', '\n')
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
    
    # Step 2: Fix common spacing issues BEFORE processing line breaks
    
    # Fix missing spaces after numbers in addresses (52ShalloakRoad -> 52 ShalloakRoad)
    cleaned = re.sub(r'(\d)([A-Z][a-z]+)', r'\1 \2', cleaned)
    
    # Fix compound words that should be separated
    # Common patterns in council documents
    cleaned = re.sub(r'followingconsultations', 'following consultations', cleaned)
    cleaned = re.sub(r'reservedwith', 'reserved with', cleaned)
    cleaned = re.sub(r'exceptionofmeans', 'exception of means', cleaned)
    cleaned = re.sub(r'anddetailed', 'and detailed', cleaned)
    cleaned = re.sub(r'incwoodland', 'inc woodland', cleaned)
    cleaned = re.sub(r'excessaccess', 'excess access', cleaned)
    
    # Fix "the" + capitalized place names
    cleaned = re.sub(r'the([A-Z][a-z]+)', r'the \1', cleaned)
    
    # Fix "to" + capitalized place names  
    cleaned = re.sub(r'to([A-Z][a-z]+)', r'to \1', cleaned)
    
    # Fix "at" + capitalized place names
    cleaned = re.sub(r'at([A-Z][a-z]+)', r'at \1', cleaned)
    
    # Fix "into" + capitalized place names
    cleaned = re.sub(r'into([A-Z][a-z]+)', r'into \1', cleaned)
    
    # Fix compound road names (common in UK addresses)
    # Pattern: [lowercase][Uppercase]Road -> [lowercase] [Uppercase] Road
    cleaned = re.sub(r'([a-z])([A-Z][a-z]+Road)', r'\1 \2', cleaned)
    
    # Fix compound road names without "Road" suffix
    # Pattern: [lowercase][Uppercase][lowercase] where it's likely a compound
    cleaned = re.sub(r'([a-z])([A-Z][a-z]*[A-Z][a-z]+)', r'\1 \2', cleaned)
    
    # Specific fixes for common UK place name patterns
    cleaned = re.sub(r'SturryLink', 'Sturry Link', cleaned)
    cleaned = re.sub(r'ShalloakRoad', 'Shalloak Road', cleaned)
    cleaned = re.sub(r'SweechbridgeRoad', 'Sweechbridge Road', cleaned)
    cleaned = re.sub(r'HillboroughRoad', 'Hillborough Road', cleaned)
    
    # Fix missing spaces around semicolons followed by letters/numbers
    cleaned = re.sub(r';([a-zA-Z0-9])', r'; \1', cleaned)
    
    # Fix missing spaces after closing parentheses followed by capital letters
    cleaned = re.sub(r'\)([A-Z])', r') \1', cleaned)
    
    # Fix missing spaces before opening parentheses preceded by letters
    cleaned = re.sub(r'([a-z])(\([a-zA-Z])', r'\1 \2', cleaned)
    
    # Fix missing spaces around "of" in addresses (upt212sqm -> up to 212 sqm)
    cleaned = re.sub(r'upt(\d)', r'up to \1', cleaned)
    cleaned = re.sub(r'(\d)(sqm|sq m)', r'\1 \2', cleaned)
    
    # Fix missing spaces in "excess access" type phrases
    cleaned = re.sub(r'excess([a-z])', r'excess \1', cleaned)
    
    # Step 3: Mark important structural breaks before we process line breaks
    # These will be preserved as actual line breaks
    
    # Mark lettered/numbered application references as new paragraphs
    # Look for patterns like ";(a)", ";(b)", etc. and make them start new lines
    cleaned = re.sub(r';(\([a-z]\))', r';\n\n\1', cleaned)
    
    # Mark numbered lists (but only if they start a clear new item)
    cleaned = re.sub(r'\.(\d+\.)\s*([A-Z])', r'.\n\n\1 \2', cleaned)
    
    # Mark important sections (these should definitely be new paragraphs)
    section_keywords = ['RESOLVED', 'RECOMMENDED', 'NOTED', 'AGREED', 'DECIDED', 'EXEMPT ITEMS']
    for keyword in section_keywords:
        # Add double break before these keywords
        pattern = r'([a-z])(' + re.escape(keyword) + r')'
        cleaned = re.sub(pattern, r'\1\n\n\2', cleaned, flags=re.IGNORECASE)
    
    # Step 4: Handle the line break conversion strategy
    # First, mark paragraph breaks (double \n\n) with a special marker
    PARAGRAPH_MARKER = "|||PARAGRAPH_BREAK|||"
    cleaned = cleaned.replace('\n\n', PARAGRAPH_MARKER)
    
    # Step 5: Convert single line breaks to spaces
    cleaned = cleaned.replace('\n', ' ')
    
    # Step 6: Restore paragraph breaks as single line breaks
    cleaned = cleaned.replace(PARAGRAPH_MARKER, '\n')
    
    # Step 7: Additional spacing improvements after line break processing
    
    # Ensure proper spacing around application references
    cleaned = re.sub(r'Application\s*([A-Z]{2}/\d+)', r'Application \1', cleaned)
    
    # Fix spacing around "and" in lists
    cleaned = re.sub(r'([a-z])and([A-Z])', r'\1 and \2', cleaned)
    
    # Improve spacing around locations and lists
    cleaned = re.sub(r'([a-z]);([A-Z])', r'\1; \2', cleaned)
    cleaned = re.sub(r'([a-z]),([A-Z][a-z])', r'\1, \2', cleaned)
    
    # Step 8: Clean up excessive whitespace
    cleaned = re.sub(r' +', ' ', cleaned)  # Multiple spaces become single space
    cleaned = re.sub(r'\n +', '\n', cleaned)  # Remove spaces after line breaks
    cleaned = re.sub(r' +\n', '\n', cleaned)  # Remove spaces before line breaks
    
    # Step 9: Clean up multiple consecutive line breaks
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Max 2 consecutive line breaks
    
    # Step 10: Final spacing fixes
    
    # Fix any remaining spacing issues around common patterns
    cleaned = re.sub(r'(\d+)([A-Z][a-z]+Road)', r'\1 \2', cleaned)  # "52ShalloakRoad" -> "52 Shalloak Road"
    cleaned = re.sub(r'(\w)(\([a-z]\))', r'\1 \2', cleaned)  # Ensure space before (a), (b), etc.
    
    # Step 11: Final cleanup
    cleaned = cleaned.strip()
    
    return cleaned


def format_agenda_results_enhanced(results: pd.DataFrame, meetings_df: pd.DataFrame,
                                   agendas_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhanced agenda results with full text and better formatting
    """
    if results.empty:
        return pd.DataFrame()

    try:
        # Merge with meetings
        if not meetings_df.empty and "meeting_id" in results.columns:
            meeting_cols = ["meeting_id"]
            if "web_meeting_code" in meetings_df.columns:
                meeting_cols.append("web_meeting_code")
            if "committee_name" in meetings_df.columns:
                meeting_cols.append("committee_name")

            results = results.merge(
                meetings_df[meeting_cols],
                on="meeting_id",
                how="left"
            )

        # Merge with agendas
        if not agendas_df.empty:
            chunk_col = "chunk_id" if "chunk_id" in results.columns else "agenda_id"
            if chunk_col in results.columns:
                agenda_cols = ["agenda_id"]
                if "item_title" in agendas_df.columns:
                    agenda_cols.append("item_title")
                if "item_text" in agendas_df.columns:
                    agenda_cols.append("item_text")

                results = results.merge(
                    agendas_df[agenda_cols],
                    left_on=chunk_col,
                    right_on="agenda_id",
                    how="left"
                )

        enhanced_results = []

        for _, row in results.iterrows():
            # Format date
            date_str = "Unknown Date"
            if "meeting_date" in row and pd.notna(row["meeting_date"]):
                try:
                    date_str = pd.to_datetime(row["meeting_date"], unit="ms").strftime("%d %b %Y")
                except:
                    pass

            # Create meeting button (copied from PDF tab)
            meeting_button = ""
            if pd.notna(row.get("web_meeting_code")):
                meeting_url = f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row['web_meeting_code']}"
                meeting_button = f'<div style="margin-top: 4px;"><a href="{meeting_url}" target="_blank" style="background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; text-decoration: none; font-weight: 500;">Meeting</a></div>'

            # Format date with button (copied from PDF tab)
            date_html = f'<span style="font-weight: 500; color: #555;">{date_str}</span>{meeting_button}'

            committee = row.get("committee_name")
            if pd.isna(committee) or not committee:
                if 'committee_id' in row and pd.notna(row.get('committee_id')):
                    committee = str(row['committee_id']).replace("-", " ").replace("_", " ").title()
                else:
                    committee = "Unknown Committee"

            item_title = row.get("item_title", "Untitled Agenda Item")
            item_text = row.get("item_text", "No content available")

            # IMPROVED TEXT CLEANING - preserves structure
            if isinstance(item_title, str):
                item_title = ' '.join(item_title.replace('\\n', '').replace('\n', '').replace('\\r', '').replace('\r', '').replace('**', '').replace('*', '').split()).strip()

            if isinstance(item_text, str):
                # Use improved cleaning that preserves meaningful breaks
                item_text = clean_agenda_text(item_text)
            
            # Create clickable agenda item title (same URL as meeting button)
            if pd.notna(row.get("web_meeting_code")):
                meeting_url = f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row['web_meeting_code']}"
                title_html = f'<a href="{meeting_url}" target="_blank" style="color: #2c3e50; text-decoration: none; font-weight: 600; font-size: 16px; border-bottom: 1px solid #2c3e50;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{item_title}</a>'
            else:
                title_html = f'<span style="color: #2c3e50; font-weight: 600; font-size: 16px;">{item_title}</span>'

            # Format with preserved line breaks using <br> tags and better styling
            formatted_text = item_text.replace('\n\n', '<br><br>').replace('\n', '<br>')
            agenda_item_html = f'<div style="margin-bottom: 8px;"><div style="margin-bottom: 6px;">{title_html}</div><div style="color: #555; font-size: 14px; line-height: 1.6; padding: 8px 0; border-left: 3px solid #e8f4f8; padding-left: 12px; background-color: #fafbfc; white-space: pre-line;">{formatted_text}</div></div>'

            # Star relevance system (copied from PDF tab)
            score = row.get('score', 1.5)
            if isinstance(score, (int, float)):
                if score <= 0.9:
                    stars = "⭐⭐⭐⭐⭐"
                elif score <= 1.1:
                    stars = "⭐⭐⭐⭐"
                elif score <= 1.3:
                    stars = "⭐⭐⭐"
                elif score <= 1.5:
                    stars = "⭐⭐"
                else:
                    stars = "⭐"
            else:
                stars = "⭐"

            enhanced_results.append({
                "Meeting Date": date_html,  # Now includes the meeting button
                "Committee": committee,
                "Agenda Item": agenda_item_html,
                "Relevance": stars  # Now uses star system instead of numeric score
            })

        return pd.DataFrame(enhanced_results)

    except Exception as e:
        st.error(f"Error formatting agenda results: {str(e)}")
        return pd.DataFrame()

def format_pdf_results_enhanced(results: pd.DataFrame, documents_df: pd.DataFrame,
                                meetings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhanced PDF results with summaries and better formatting
    """
    if results.empty:
        return pd.DataFrame()

    try:
        enhanced_results = []

        for _, row in results.iterrows():
            date_str = "Unknown Date"
            if "meeting_date" in row and pd.notna(row["meeting_date"]):
                try:
                    date_str = pd.to_datetime(row["meeting_date"], unit="ms").strftime("%d %b %Y")
                except:
                    pass

            meeting_button = ""
            if pd.notna(row.get("web_meeting_code")):
                meeting_url = f"https://democracy.kent.gov.uk/ieListDocuments.aspx?MId={row['web_meeting_code']}"
                meeting_button = f'<div style="margin-top: 4px;"><a href="{meeting_url}" target="_blank" style="background-color: #6c757d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; text-decoration: none; font-weight: 500;">Meeting</a></div>'

            date_html = f'<span style="font-weight: 500; color: #555;">{date_str}</span>{meeting_button}'

            committee = row.get('committee_name')
            if pd.isna(committee) or not committee:
                if 'committee_id' in row and pd.notna(row.get('committee_id')):
                    committee = str(row['committee_id']).replace("-", " ").replace("_", " ").title()
                else:
                    committee = 'Unknown Committee'

            # FIXED: Handle display_title column suffixes from merge
            doc_title = None
            
            # Try different display_title column names (due to merge suffixes)
            for col_name in ['display_title', 'display_title_y', 'display_title_x']:
                if col_name in row and pd.notna(row.get(col_name)) and str(row.get(col_name)).strip():
                    doc_title = row.get(col_name)
                    break
            
            # If no display_title found, use filename fallback
            if not doc_title:
                doc_title = row.get("source_filename", "Document")
                if isinstance(doc_title, str):
                    # Remove file extension and clean up filename
                    doc_title = doc_title.replace('.pdf', '').replace('.doc', '').replace('.docx', '')
                    # Replace underscores and dashes with spaces
                    doc_title = doc_title.replace('_', ' ').replace('-', ' ')
                    # Capitalize words properly
                    doc_title = ' '.join(word.capitalize() for word in doc_title.split())

            if isinstance(doc_title, str):
                # Clean up the display title
                doc_title = ' '.join(doc_title.replace('\\n', '').replace('\n', '').replace('**', '').replace('*', '').split()).strip()
                # Ensure proper capitalization for display
                if doc_title and not any(c.isupper() for c in doc_title):
                    doc_title = doc_title.title()

            # FIXED URL HANDLING - More robust approach
            doc_url = row.get("url")
            title_html = ""
            
            if pd.notna(doc_url) and doc_url and str(doc_url).strip():
                # Clean and prepare the URL
                clean_url = str(doc_url).strip()
                
                # If URL doesn't start with http/https, add https://
                if not clean_url.startswith(('http://', 'https://')):
                    clean_url = 'https://' + clean_url
                
                # Simple URL encoding for common problematic characters
                clean_url = clean_url.replace(' ', '%20').replace('(', '%28').replace(')', '%29')
                
                # Create clickable link
                title_html = f'<a href="{clean_url}" target="_blank" style="color: #2c3e50; text-decoration: none; font-weight: 600; font-size: 16px; border-bottom: 1px solid #2c3e50;" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{doc_title}</a>'
                
                # Debug info (remove this in production)
                # title_html += f'<br><small style="color: #666; font-size: 10px;">URL: {clean_url}</small>'
            else:
                # No URL available - just show title
                title_html = f'<span style="color: #2c3e50; font-weight: 600; font-size: 16px;">{doc_title}</span>'

            doc_type = "Document"
            doc_type_color = "#6c757d"
            if "doc_category" in row and pd.notna(row["doc_category"]):
                type_mapping = {
                    "prod": ("Report", "#007bff"),
                    "eqia": ("Impact Assessment", "#28a745"),
                    "other": ("Document", "#6c757d"),
                    "minutes": ("Minutes", "#ffc107")
                }
                doc_type, doc_type_color = type_mapping.get(str(row["doc_category"]).lower(), ("Document", "#6c757d"))

            summary = row.get("summary", "No summary available")
            if isinstance(summary, str):
                summary = ' '.join(summary.replace('\\n', ' ').replace('\n', ' ').replace('\\r', ' ').replace('\r', ' ').replace('**', '').replace('*', '').split()).strip()

            document_html = f'<div style="margin-bottom: 8px;">{title_html}<div style="color: #555; font-size: 14px; margin-top: 8px; line-height: 1.5; padding: 8px 0; border-left: 3px solid #e8f4f8; padding-left: 12px; background-color: #fafbfc;">{summary}</div></div>'

            score = row.get('score', 1.5)
            if isinstance(score, (int, float)):
                if score <= 0.9:
                    stars = "⭐⭐⭐⭐⭐"
                elif score <= 1.1:
                    stars = "⭐⭐⭐⭐"
                elif score <= 1.3:
                    stars = "⭐⭐⭐"
                elif score <= 1.5:
                    stars = "⭐⭐"
                else:
                    stars = "⭐"
            else:
                stars = "⭐"

            enhanced_results.append({
                "Meeting Date": date_html,
                "Committee": committee,
                "Document": document_html,
                "Relevance": stars
            })

        return pd.DataFrame(enhanced_results)

    except Exception as e:
        st.error(f"Error formatting PDF results: {str(e)}")
        return pd.DataFrame()

def display_results_with_pagination(df: pd.DataFrame, results_per_page: int = 5,
                                     key_prefix: str = "") -> None:
    if df.empty:
        st.info("No results found for your search query.")
        return

    total_results = len(df)
    total_pages = (total_results - 1) // results_per_page + 1

    if f"{key_prefix}_current_page" not in st.session_state:
        st.session_state[f"{key_prefix}_current_page"] = 1

    current_page = st.session_state[f"{key_prefix}_current_page"]
    if current_page > total_pages:
        current_page = 1
        st.session_state[f"{key_prefix}_current_page"] = 1

    start_idx = (current_page - 1) * results_per_page
    end_idx = min(start_idx + results_per_page, total_results)
    page_df = df.iloc[start_idx:end_idx]

    _apply_results_css()
    st.markdown(f'<div class="council-results">{page_df.to_html(escape=False, index=False)}</div>',
                unsafe_allow_html=True)

    if total_pages > 1:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("← Previous", disabled=(current_page <= 1), key=f"{key_prefix}_prev"):
                st.session_state[f"{key_prefix}_current_page"] = current_page - 1
                st.rerun()

        with col2:
            page = st.selectbox(
                f"Page {current_page} of {total_pages} (showing {end_idx - start_idx} results)",
                range(1, total_pages + 1),
                index=current_page - 1,
                key=f"{key_prefix}_page_select"
            )
            if page != current_page:
                st.session_state[f"{key_prefix}_current_page"] = page
                st.rerun()

        with col3:
            if st.button("Next →", disabled=(current_page >= total_pages), key=f"{key_prefix}_next"):
                st.session_state[f"{key_prefix}_current_page"] = current_page + 1
                st.rerun()


def _apply_results_css() -> None:
    st.markdown("""
    <style>
    .council-results table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-radius: 8px;
        overflow: hidden;
    }
    .council-results th {
        background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
        color: white;
        font-weight: 600;
        padding: 12px 8px;
        text-align: left;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .council-results td {
        padding: 15px 10px;
        border-bottom: 1px solid #e9ecef;
        vertical-align: top;
        font-size: 14px;
        line-height: 1.4;
    }
    .council-results tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .council-results tr:hover {
        background-color: #e3f2fd;
        transition: background-color 0.2s ease;
    }
    .council-results a {
        color: #1f77b4;
        text-decoration: none;
    }
    .council-results a:hover {
        text-decoration: underline;
        color: #0d47a1;
    }
    .council-results td:first-child {
        font-weight: 500;
        width: 140px;
        font-size: 13px;
    }
    .council-results td:nth-child(2) {
        width: 180px;
        font-weight: 500;
        font-size: 14px;
    }
    .council-results td:nth-child(3) {
        width: auto;
        font-size: 14px;
    }
    .council-results td:last-child {
        width: 100px;
        text-align: center;
        font-size: 18px;
        background-color: #f1f3f4;
    }
    </style>
    """, unsafe_allow_html=True)
