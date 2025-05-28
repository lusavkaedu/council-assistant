"""
User feedback system for Council Assistant
Provides UI components for collecting user feedback and bug reports
"""
import streamlit as st
from typing import Optional
from .logging_system import log_feedback, log_interaction

def show_feedback_sidebar():
    """Add feedback section to sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Feedback")
        
        if st.button("💬 Give Feedback", key="feedback_button"):
            st.session_state.show_feedback = True
        
        if st.button("🐛 Report Bug", key="bug_button"):
            st.session_state.show_bug_report = True

def show_feedback_modal():
    """Show feedback modal dialog"""
    if st.session_state.get("show_feedback", False):
        with st.container():
            st.markdown("### 💬 Your Feedback")
            st.markdown("Help us improve Kent County Council Records Search!")
            
            # Feedback form
            feedback_type = st.selectbox(
                "What type of feedback?",
                ["General Feedback", "Feature Request", "Search Quality", "Interface Improvement"],
                key="feedback_type"
            )
            
            rating = st.slider(
                "How would you rate your experience? (1=Poor, 5=Excellent)",
                min_value=1, max_value=5, value=3,
                key="feedback_rating"
            )
            
            message = st.text_area(
                "Please share your thoughts:",
                placeholder="What's working well? What could be improved?",
                height=100,
                key="feedback_message"
            )
            
            contact_info = st.text_input(
                "Email (optional - for follow-up):",
                placeholder="your.email@example.com",
                key="feedback_contact"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Submit Feedback", type="primary", key="submit_feedback_btn"):
                    if message.strip():
                        # Log the feedback
                        log_feedback(
                            feedback_type=feedback_type,
                            message=message,
                            rating=rating,
                            contact_info=contact_info if contact_info.strip() else None,
                            query_context=st.session_state.get("query", "")
                        )
                        
                        st.success("Thank you for your feedback! 🙏")
                        st.session_state.show_feedback = False
                        st.rerun()
                    else:
                        st.error("Please enter your feedback message.")
            
            with col2:
                if st.button("Cancel", key="cancel_feedback_btn"):
                    st.session_state.show_feedback = False
                    st.rerun()

def show_bug_report_modal():
    """Show bug report modal dialog"""
    if st.session_state.get("show_bug_report", False):
        with st.container():
            st.markdown("### 🐛 Report a Bug")
            st.markdown("Help us fix issues by describing what went wrong.")
            
            # Bug report form
            bug_type = st.selectbox(
                "What type of issue?",
                ["Search not working", "Results incorrect", "Page loading error", "Interface problem", "Other"],
                key="bug_type"
            )
            
            current_query = st.session_state.get("query", "")
            if current_query:
                st.info(f"Current search: '{current_query}'")
            
            description = st.text_area(
                "Describe the problem:",
                placeholder="What were you trying to do? What happened instead? Include any error messages you saw.",
                height=120,
                key="bug_description"
            )
            
            steps = st.text_area(
                "Steps to reproduce (optional):",
                placeholder="1. I searched for...\n2. I clicked on...\n3. Then I saw...",
                height=80,
                key="bug_steps"
            )
            
            contact_info = st.text_input(
                "Email (optional - for follow-up):",
                placeholder="your.email@example.com",
                key="bug_contact"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Submit Bug Report", type="primary", key="submit_bug_btn"):
                    if description.strip():
                        # Combine description and steps
                        full_message = description
                        if steps.strip():
                            full_message += f"\n\nSteps to reproduce:\n{steps}"
                        
                        # Log the bug report
                        log_feedback(
                            feedback_type=f"Bug Report - {bug_type}",
                            message=full_message,
                            contact_info=contact_info if contact_info.strip() else None,
                            query_context=current_query
                        )
                        
                        st.success("Bug report submitted! We'll investigate this issue. 🔍")
                        st.session_state.show_bug_report = False
                        st.rerun()
                    else:
                        st.error("Please describe the problem you encountered.")
            
            with col2:
                if st.button("Cancel", key="cancel_bug_btn"):
                    st.session_state.show_bug_report = False
                    st.rerun()

def show_quick_feedback():
    """Show quick feedback thumbs up/down buttons"""
    if st.session_state.get("query") and (
        st.session_state.get("agenda_results") is not None or 
        st.session_state.get("pdf_results") is not None
    ):
        st.markdown("---")
        st.markdown("**Was this search helpful?**")
        
        col1, col2, col3 = st.columns([1, 1, 8])  # Changed from [1, 1, 3] to [1, 1, 8]
        
        with col1:
            if st.button("👍", help="Yes, helpful", key="thumbs_up_btn"):
                log_feedback(
                    feedback_type="Quick Feedback",
                    message="Thumbs up - search was helpful",
                    rating=4,
                    query_context=st.session_state.get("query", "")
                )
                st.success("Thanks! 👍")
        
        with col2:
            if st.button("👎", help="Not helpful", key="thumbs_down_btn"):
                log_feedback(
                    feedback_type="Quick Feedback", 
                    message="Thumbs down - search was not helpful",
                    rating=2,
                    query_context=st.session_state.get("query", "")
                )
                st.info("Thanks for letting us know. Consider using the feedback button for more details.")

def log_tab_change(tab_name: str):
    """Log when user changes tabs"""
    log_interaction("tab_change", details={"tab_name": tab_name})

def log_filter_usage(filter_type: str, filter_value: str):
    """Log when user uses filters"""
    log_interaction("filter_usage", details={
        "filter_type": filter_type,
        "filter_value": filter_value
    })

def log_pagination(page_number: int, results_per_page: int, result_type: str):
    """Log pagination usage"""
    log_interaction("pagination", details={
        "page_number": page_number,
        "results_per_page": results_per_page,
        "result_type": result_type
    })

def log_ai_summary_request():
    """Log when user requests AI summary"""
    log_interaction("ai_summary_request", details={
        "query": st.session_state.get("query", ""),
        "has_agenda_results": "agenda_results" in st.session_state,
        "has_pdf_results": "pdf_results" in st.session_state
    })