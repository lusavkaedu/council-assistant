"""
Semantic search functionality using FAISS and OpenAI embeddings
"""
import numpy as np
import pandas as pd
import faiss
from openai import OpenAI
import streamlit as st
from pathlib import Path


def get_embedding(query: str, client: OpenAI) -> np.ndarray:
    """
    Generate embedding vector for search query using OpenAI API
    
    Args:
        query: Search query string
        client: OpenAI client instance
        
    Returns:
        numpy array of embedding vector, or None if failed
    """
    try:
        response = client.embeddings.create(
            input=[query],
            model="text-embedding-3-small"
        )
        return np.array(response.data[0].embedding, dtype=np.float32).reshape(1, -1)
    except Exception as e:
        st.error(f"Embedding generation failed: {str(e)}")
        return None


@st.cache_resource
def load_search_index(index_path: str) -> faiss.Index:
    """
    Load FAISS index with error handling and caching
    
    Args:
        index_path: Path to FAISS index file
        
    Returns:
        FAISS index object or None if failed
    """
    try:
        if not Path(index_path).exists():
            st.error(f"Missing index file: {index_path}")
            return None
        return faiss.read_index(str(index_path))
    except Exception as e:
        st.error(f"Failed to load search index: {str(e)}")
        return None


def search_agendas(query: str, client: OpenAI, index: faiss.Index, 
                  metadata_df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """
    Search agenda items using FAISS semantic search
    
    Args:
        query: Search query string
        client: OpenAI client instance
        index: FAISS index for agenda items
        metadata_df: DataFrame with agenda metadata
        k: Number of results to return
        
    Returns:
        DataFrame with search results and scores
    """
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


def search_pdfs(query: str, client: OpenAI, index: faiss.Index, 
               metadata_df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """
    Search PDF documents using FAISS semantic search
    
    Args:
        query: Search query string
        client: OpenAI client instance
        index: FAISS index for PDF summaries
        metadata_df: DataFrame with PDF metadata
        k: Number of results to return
        
    Returns:
        DataFrame with search results and scores
    """
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


def sort_results(results_df: pd.DataFrame, sort_method: str) -> pd.DataFrame:
    """
    Sort search results based on user preference
    
    Args:
        results_df: DataFrame with search results
        sort_method: Sorting method string
        
    Returns:
        Sorted DataFrame
    """
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

    # Default to relevance sorting
    if "score" in results_df.columns:
        return results_df.sort_values("score", ascending=True)

    return results_df
