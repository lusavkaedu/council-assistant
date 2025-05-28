"""
AI analysis functionality for generating intelligent summaries of search results
"""
import pandas as pd
from openai import OpenAI


def build_ai_prompt(query: str, agenda_results: pd.DataFrame, pdf_results: pd.DataFrame, 
                   agendas_df: pd.DataFrame, meetings_df: pd.DataFrame, 
                   documents_df: pd.DataFrame) -> str:
    """
    Build complete AI prompt with all metadata from search results
    
    Args:
        query: Original search query
        agenda_results: DataFrame with agenda search results
        pdf_results: DataFrame with PDF search results
        agendas_df: Full agendas metadata DataFrame
        meetings_df: Full meetings metadata DataFrame
        documents_df: Full documents metadata DataFrame
        
    Returns:
        Complete prompt string for AI analysis
    """
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


def generate_ai_analysis(query: str, agenda_results: pd.DataFrame, pdf_results: pd.DataFrame,
                        agendas_df: pd.DataFrame, meetings_df: pd.DataFrame, 
                        documents_df: pd.DataFrame, client: OpenAI, 
                        model: str = "gpt-4o-mini") -> str:
    """
    Generate AI analysis of search results
    
    Args:
        query: Original search query
        agenda_results: DataFrame with agenda search results
        pdf_results: DataFrame with PDF search results
        agendas_df: Full agendas metadata DataFrame
        meetings_df: Full meetings metadata DataFrame
        documents_df: Full documents metadata DataFrame
        client: OpenAI client instance
        model: GPT model to use
        
    Returns:
        AI-generated analysis text
    """
    prompt = build_ai_prompt(
        query=query,
        agenda_results=agenda_results,
        pdf_results=pdf_results,
        agendas_df=agendas_df,
        meetings_df=meetings_df,
        documents_df=documents_df
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You're a council policy analyst helping citizens understand local government decisions and policies."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        raise Exception(f"AI analysis generation failed: {str(e)}")


def get_analysis_source_info(agenda_results: pd.DataFrame, pdf_results: pd.DataFrame) -> dict:
    """
    Get source information for the analysis
    
    Args:
        agenda_results: DataFrame with agenda search results
        pdf_results: DataFrame with PDF search results
        
    Returns:
        Dictionary with source counts and information
    """
    return {
        "agenda_count": len(agenda_results) if not agenda_results.empty else 0,
        "pdf_count": len(pdf_results) if not pdf_results.empty else 0,
        "total_sources": (len(agenda_results) if not agenda_results.empty else 0) + 
                        (len(pdf_results) if not pdf_results.empty else 0)
    }
