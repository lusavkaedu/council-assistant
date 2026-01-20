"""
Data loading utilities for Council Assistant
"""
import pandas as pd
import jsonlines
import streamlit as st
from pathlib import Path
from typing import Dict


def load_jsonl_safe(filepath: Path) -> pd.DataFrame:
    """
    Load a .jsonl file with error handling
    
    Args:
        filepath: Path to the .jsonl file
        
    Returns:
        DataFrame with loaded data, or empty DataFrame if failed
    """
    try:
        if not filepath.exists():
            st.error(f"Missing file: {filepath}")
            return pd.DataFrame()
        
        with jsonlines.open(filepath) as reader:
            return pd.DataFrame(list(reader))  # Convert to list first
            
    except Exception as e:
        st.error(f"Failed to load {filepath}: {str(e)}")
        return pd.DataFrame()


@st.cache_data
def load_base_data(paths: Dict[str, Path]) -> Dict[str, pd.DataFrame]:
    """
    Load essential datasets with caching
    
    Args:
        paths: Dictionary of file paths
        
    Returns:
        Dictionary of loaded DataFrames
    """
    return {
        "documents": load_jsonl_safe(paths["pdf_warehouse"]),  # Single source of truth
        "meetings": load_jsonl_safe(paths["meetings"]),
        "agendas": load_jsonl_safe(paths["agendas"])
    }


@st.cache_data
def load_search_metadata(paths: Dict[str, Path]) -> Dict[str, pd.DataFrame]:
    """
    Load search index metadata with caching
    
    Args:
        paths: Dictionary of file paths
        
    Returns:
        Dictionary of loaded metadata DataFrames
    """
    return {
        "agenda_metadata": load_jsonl_safe(paths["agenda_metadata"]),
        "pdf_metadata": load_jsonl_safe(paths["pdf_metadata"])
    }


def validate_data_integrity(data: Dict[str, pd.DataFrame]) -> bool:
    """
    Validate that essential data is loaded correctly
    
    Args:
        data: Dictionary of DataFrames to validate
        
    Returns:
        True if data is valid, False otherwise
    """
    essential_datasets = ["documents", "meetings", "agendas"]
    
    for dataset_name in essential_datasets:
        if dataset_name not in data or data[dataset_name].empty:
            st.error(f"❌ Critical dataset '{dataset_name}' failed to load or is empty")
            return False
    
    return True


def get_data_summary(data: Dict[str, pd.DataFrame]) -> Dict[str, int]:
    """
    Get summary statistics for loaded data
    
    Args:
        data: Dictionary of loaded DataFrames
        
    Returns:
        Dictionary with counts for each dataset
    """
    return {
        name: len(df) if not df.empty else 0 
        for name, df in data.items()
    }
