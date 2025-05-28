"""
Comprehensive logging system for Council Assistant
Tracks user interactions, search queries, errors, and performance metrics
"""
import logging
import json
import datetime
from pathlib import Path
import streamlit as st
from typing import Dict, Any, Optional
import pandas as pd

class CouncilLogger:
    """
    Centralized logging system for the Council Assistant application
    """
    
    def __init__(self, log_dir: Path = None):
        if log_dir is None:
            log_dir = Path("/Users/lgfolder/github/council-assistant/logs")
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Set up different log files
        self.search_log = self.log_dir / "search_queries.jsonl"
        self.error_log = self.log_dir / "errors.jsonl"
        self.performance_log = self.log_dir / "performance.jsonl"
        self.user_log = self.log_dir / "user_interactions.jsonl"
        self.feedback_log = self.log_dir / "user_feedback.jsonl"
        
        # Set up Python logging
        self._setup_python_logging()
    
    def _setup_python_logging(self):
        """Set up standard Python logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_dir / "application.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("CouncilAssistant")
    
    def _write_jsonl(self, filepath: Path, data: Dict[str, Any]):
        """Write a single JSON line to a log file"""
        try:
            # Ensure the directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Create the file if it doesn't exist
            if not filepath.exists():
                filepath.touch()
            
            with open(filepath, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
                f.write('\n')
        except Exception as e:
            self.logger.error(f"Failed to write to {filepath}: {str(e)}")
    
    def _get_session_info(self) -> Dict[str, Any]:
        """Get basic session information"""
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": st.session_state.get("session_id", "unknown"),
            "user_agent": st.context.headers.get("User-Agent", "unknown") if hasattr(st.context, 'headers') else "unknown"
        }
    
    def log_search_query(self, query: str, tab_name: str, results_count: int, 
                        search_time: float = None, filters: Dict = None):
        """Log search queries and their results"""
        log_entry = {
            **self._get_session_info(),
            "event_type": "search_query",
            "query": query,
            "tab_name": tab_name,
            "results_count": results_count,
            "search_time_seconds": search_time,
            "filters": filters or {},
            "query_length": len(query),
            "query_word_count": len(query.split())
        }
        self._write_jsonl(self.search_log, log_entry)
        self.logger.info(f"Search: '{query}' in {tab_name} -> {results_count} results")
    
    def log_error(self, error_type: str, error_message: str, context: Dict = None):
        """Log application errors"""
        log_entry = {
            **self._get_session_info(),
            "event_type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        self._write_jsonl(self.error_log, log_entry)
        self.logger.error(f"{error_type}: {error_message}")
    
    def log_performance(self, operation: str, duration: float, details: Dict = None):
        """Log performance metrics"""
        log_entry = {
            **self._get_session_info(),
            "event_type": "performance",
            "operation": operation,
            "duration_seconds": duration,
            "details": details or {}
        }
        self._write_jsonl(self.performance_log, log_entry)
        self.logger.info(f"Performance: {operation} took {duration:.2f}s")
    
    def log_user_interaction(self, interaction_type: str, details: Dict = None):
        """Log user interactions (tab changes, filter usage, etc.)"""
        log_entry = {
            **self._get_session_info(),
            "event_type": "user_interaction",
            "interaction_type": interaction_type,
            "details": details or {}
        }
        self._write_jsonl(self.user_log, log_entry)
    
    def log_feedback(self, feedback_type: str, message: str, rating: int = None, 
                    contact_info: str = None, query_context: str = None):
        """Log user feedback"""
        log_entry = {
            **self._get_session_info(),
            "event_type": "user_feedback",
            "feedback_type": feedback_type,
            "message": message,
            "rating": rating,
            "contact_info": contact_info,
            "query_context": query_context
        }
        self._write_jsonl(self.feedback_log, log_entry)
        self.logger.info(f"Feedback received: {feedback_type}")
    
    def get_search_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get search analytics for the last N days"""
        try:
            if not self.search_log.exists():
                return {"error": "No search log found"}
            
            # Read search logs
            searches = []
            with open(self.search_log, 'r') as f:
                for line in f:
                    try:
                        searches.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            if not searches:
                return {"total_searches": 0}
            
            df = pd.DataFrame(searches)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter to last N days
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            recent_df = df[df['timestamp'] > cutoff_date]
            
            analytics = {
                "total_searches": len(recent_df),
                "unique_queries": recent_df['query'].nunique(),
                "most_popular_queries": recent_df['query'].value_counts().head(10).to_dict(),
                "tab_usage": recent_df['tab_name'].value_counts().to_dict(),
                "average_results_per_search": recent_df['results_count'].mean(),
                "zero_result_searches": len(recent_df[recent_df['results_count'] == 0]),
                "search_success_rate": 1 - (len(recent_df[recent_df['results_count'] == 0]) / len(recent_df))
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error generating analytics: {str(e)}")
            return {"error": str(e)}
    
    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get error summary for the last N days"""
        try:
            if not self.error_log.exists():
                return {"total_errors": 0}
            
            errors = []
            with open(self.error_log, 'r') as f:
                for line in f:
                    try:
                        errors.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            if not errors:
                return {"total_errors": 0}
            
            df = pd.DataFrame(errors)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            recent_df = df[df['timestamp'] > cutoff_date]
            
            return {
                "total_errors": len(recent_df),
                "error_types": recent_df['error_type'].value_counts().to_dict(),
                "recent_errors": recent_df.tail(5)[['timestamp', 'error_type', 'error_message']].to_dict('records')
            }
            
        except Exception as e:
            return {"error": str(e)}

# Global logger instance
logger = CouncilLogger()

# Convenience functions for easy import
def log_search(query: str, tab_name: str, results_count: int, **kwargs):
    """Convenience function for logging searches"""
    logger.log_search_query(query, tab_name, results_count, **kwargs)

def log_error(error_type: str, error_message: str, **kwargs):
    """Convenience function for logging errors"""
    logger.log_error(error_type, error_message, **kwargs)

def log_performance(operation: str, duration: float, **kwargs):
    """Convenience function for logging performance"""
    logger.log_performance(operation, duration, **kwargs)

def log_interaction(interaction_type: str, **kwargs):
    """Convenience function for logging user interactions"""
    logger.log_user_interaction(interaction_type, **kwargs)

def log_feedback(feedback_type: str, message: str, **kwargs):
    """Convenience function for logging feedback"""
    logger.log_feedback(feedback_type, message, **kwargs)