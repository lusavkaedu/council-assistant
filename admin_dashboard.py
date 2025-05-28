# Standalone Admin Dashboard for Council Assistant
# Save this as: admin_dashboard.py (separate from your main app)
# Run with: streamlit run admin_dashboard.py --server.port 8502

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Council Assistant - Admin Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin-bottom: 1rem;
    }
    .alert-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin-bottom: 1rem;
    }
    .success-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
    .error-card {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
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
        background-color: #007bff;
        color: white;
        border-color: #007bff;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
    <h1 style="color: white; margin: 0;">📊 Council Assistant - Admin Dashboard</h1>
    <p style="color: #e3f2fd; margin: 0.5rem 0 0 0;">Real-time analytics and system monitoring</p>
</div>
""", unsafe_allow_html=True)

# Configuration
LOG_DIR = Path("/Users/lgfolder/github/council-assistant/logs")

# Sidebar configuration
with st.sidebar:
    st.markdown("### ⚙️ Dashboard Settings")
    
    # Time period selector
    time_period = st.selectbox(
        "📅 Time Period", 
        [1, 7, 30, 90], 
        index=1, 
        format_func=lambda x: f"Last {x} days"
    )
    
    # Auto-refresh option
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()
    
    # Manual refresh
    if st.button("🔄 Refresh Now", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📁 Log Files Status")
    
    # Check log files
    log_files = {
        "Search Queries": LOG_DIR / "search_queries.jsonl",
        "User Feedback": LOG_DIR / "user_feedback.jsonl", 
        "User Interactions": LOG_DIR / "user_interactions.jsonl",
        "Errors": LOG_DIR / "errors.jsonl",
        "Performance": LOG_DIR / "performance.jsonl"
    }
    
    for name, path in log_files.items():
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            st.success(f"✅ {name} ({size:.1f} KB)")
        else:
            st.error(f"❌ {name} (missing)")

# Data loading functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_log_data():
    """Load all log data with caching"""
    data = {
        'searches': [],
        'feedback': [],
        'interactions': [],
        'errors': [],
        'performance': []
    }
    
    # Load search queries
    search_file = LOG_DIR / "search_queries.jsonl"
    if search_file.exists():
        with open(search_file, 'r') as f:
            for line in f:
                try:
                    data['searches'].append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Load feedback
    feedback_file = LOG_DIR / "user_feedback.jsonl"
    if feedback_file.exists():
        with open(feedback_file, 'r') as f:
            for line in f:
                try:
                    data['feedback'].append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Load interactions
    interactions_file = LOG_DIR / "user_interactions.jsonl"
    if interactions_file.exists():
        with open(interactions_file, 'r') as f:
            for line in f:
                try:
                    data['interactions'].append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Load errors
    errors_file = LOG_DIR / "errors.jsonl"
    if errors_file.exists():
        with open(errors_file, 'r') as f:
            for line in f:
                try:
                    data['errors'].append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    # Load performance
    performance_file = LOG_DIR / "performance.jsonl"
    if performance_file.exists():
        with open(performance_file, 'r') as f:
            for line in f:
                try:
                    data['performance'].append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    return data

def calculate_metrics(data, days=7):
    """Calculate key metrics for the dashboard"""
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    
    # Convert to DataFrames
    searches_df = pd.DataFrame(data['searches'])
    feedback_df = pd.DataFrame(data['feedback'])
    errors_df = pd.DataFrame(data['errors'])
    interactions_df = pd.DataFrame(data['interactions'])
    performance_df = pd.DataFrame(data['performance'])
    
    # Filter by date
    if not searches_df.empty:
        searches_df['timestamp'] = pd.to_datetime(searches_df['timestamp'])
        recent_searches = searches_df[searches_df['timestamp'] > cutoff]
    else:
        recent_searches = pd.DataFrame()
    
    if not feedback_df.empty:
        feedback_df['timestamp'] = pd.to_datetime(feedback_df['timestamp'])
        recent_feedback = feedback_df[feedback_df['timestamp'] > cutoff]
    else:
        recent_feedback = pd.DataFrame()
    
    if not errors_df.empty:
        errors_df['timestamp'] = pd.to_datetime(errors_df['timestamp'])
        recent_errors = errors_df[errors_df['timestamp'] > cutoff]
    else:
        recent_errors = pd.DataFrame()
    
    if not performance_df.empty:
        performance_df['timestamp'] = pd.to_datetime(performance_df['timestamp'])
        recent_performance = performance_df[performance_df['timestamp'] > cutoff]
    else:
        recent_performance = pd.DataFrame()
    
    # Calculate metrics
    metrics = {
        'total_searches': len(recent_searches),
        'unique_users': recent_searches['session_id'].nunique() if not recent_searches.empty else 0,
        'avg_results_per_search': recent_searches['results_count'].mean() if not recent_searches.empty else 0,
        'zero_result_searches': len(recent_searches[recent_searches['results_count'] == 0]) if not recent_searches.empty else 0,
        'search_success_rate': 1 - (len(recent_searches[recent_searches['results_count'] == 0]) / len(recent_searches)) if not recent_searches.empty else 0,
        'total_feedback': len(recent_feedback),
        'avg_rating': recent_feedback['rating'].mean() if not recent_feedback.empty and 'rating' in recent_feedback.columns else 0,
        'total_errors': len(recent_errors),
        'avg_search_time': recent_searches['search_time_seconds'].mean() if not recent_searches.empty and 'search_time_seconds' in recent_searches.columns and recent_searches['search_time_seconds'].notna().any() else 0,
        'avg_data_load_time': recent_performance[recent_performance['operation'] == 'data_loading']['duration_seconds'].mean() if not recent_performance.empty else 0
    }
    
    return metrics, recent_searches, recent_feedback, recent_errors, recent_performance

# Load data
try:
    with st.spinner("Loading analytics data..."):
        data = load_log_data()
        metrics, searches_df, feedback_df, errors_df, performance_df = calculate_metrics(data, days=time_period)
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    if st.button("🔧 Show Debug Info"):
        st.write(f"Log directory: {LOG_DIR}")
        st.write(f"Directory exists: {LOG_DIR.exists()}")
        if LOG_DIR.exists():
            st.write(f"Files in directory: {list(LOG_DIR.glob('*.jsonl'))}")
    st.stop()

# Key Metrics Row
st.markdown("### 📊 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="margin: 0; color: #007bff;">🔍 {metrics['total_searches']:,}</h3>
        <p style="margin: 0; color: #6c757d;">Total Searches</p>
        <small style="color: #28a745;">👥 {metrics['unique_users']} unique users</small>
    </div>
    """, unsafe_allow_html=True)

with col2:
    success_rate = metrics['search_success_rate'] * 100
    color = "#28a745" if success_rate > 80 else "#ffc107" if success_rate > 60 else "#dc3545"
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="margin: 0; color: {color};">📊 {success_rate:.1f}%</h3>
        <p style="margin: 0; color: #6c757d;">Search Success Rate</p>
        <small style="color: #6c757d;">{metrics['zero_result_searches']} zero results</small>
    </div>
    """, unsafe_allow_html=True)

with col3:
    rating_color = "#28a745" if metrics['avg_rating'] > 3.5 else "#ffc107" if metrics['avg_rating'] > 2.5 else "#dc3545"
    rating_display = f"{metrics['avg_rating']:.1f}" if metrics['avg_rating'] > 0 else "N/A"
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="margin: 0; color: {rating_color};">⭐ {rating_display}</h3>
        <p style="margin: 0; color: #6c757d;">Average Rating</p>
        <small style="color: #6c757d;">📝 {metrics['total_feedback']} feedback items</small>
    </div>
    """, unsafe_allow_html=True)

with col4:
    error_color = "#dc3545" if metrics['total_errors'] > 10 else "#ffc107" if metrics['total_errors'] > 5 else "#28a745"
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="margin: 0; color: {error_color};">⚠️ {metrics['total_errors']}</h3>
        <p style="margin: 0; color: #6c757d;">Total Errors</p>
        <small style="color: #6c757d;">Last {time_period} days</small>
    </div>
    """, unsafe_allow_html=True)

# System Health Alerts
if metrics['total_errors'] > 10:
    st.markdown(f"""
    <div class="error-card">
        <h4 style="margin: 0;">🚨 High Error Rate Alert</h4>
        <p style="margin: 0.5rem 0 0 0;">{metrics['total_errors']} errors in the last {time_period} days. Investigation recommended.</p>
    </div>
    """, unsafe_allow_html=True)

if metrics['search_success_rate'] < 0.7 and metrics['total_searches'] > 0:
    st.markdown(f"""
    <div class="alert-card">
        <h4 style="margin: 0;">⚠️ Low Search Success Rate</h4>
        <p style="margin: 0.5rem 0 0 0;">Only {metrics['search_success_rate']*100:.1f}% of searches return results. Consider content expansion.</p>
    </div>
    """, unsafe_allow_html=True)

if metrics['avg_search_time'] > 3:
    st.markdown(f"""
    <div class="alert-card">
        <h4 style="margin: 0;">🐌 Slow Search Performance</h4>
        <p style="margin: 0.5rem 0 0 0;">Average search time is {metrics['avg_search_time']:.1f} seconds. Consider optimization.</p>
    </div>
    """, unsafe_allow_html=True)

# Main Dashboard Tabs
tabs = st.tabs(["📈 Analytics", "💬 User Feedback", "🔍 Search Patterns", "⚠️ System Health", "📋 Raw Data"])

with tabs[0]:  # Analytics
    if not searches_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📅 Search Activity Over Time")
            searches_df['date'] = searches_df['timestamp'].dt.date
            daily_searches = searches_df.groupby('date').size().reset_index()
            daily_searches.columns = ['Date', 'Searches']
            
            fig = px.line(daily_searches, x='Date', y='Searches', 
                         title="Daily Search Volume", markers=True)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 🎯 Tab Usage Distribution")
            if 'tab_name' in searches_df.columns:
                tab_usage = searches_df['tab_name'].value_counts()
                
                fig = px.pie(values=tab_usage.values, names=tab_usage.index,
                            title="Search Distribution by Tab")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tab usage data available")

        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔥 Most Popular Search Terms")
            popular_queries = searches_df['query'].value_counts().head(10)
            
            fig = px.bar(x=popular_queries.values, y=popular_queries.index,
                        orientation='h', title="Top 10 Search Queries")
            fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### ⚡ Search Performance Distribution")
            # Fixed search performance section
            if 'search_time_seconds' in searches_df.columns:
                valid_search_times = searches_df[searches_df['search_time_seconds'].notnull()].copy()
                if not valid_search_times.empty:
                    valid_search_times['performance_category'] = pd.cut(
                        valid_search_times['search_time_seconds'], 
                        bins=[0, 1, 2, 5, float('inf')], 
                        labels=['Fast (<1s)', 'Good (1-2s)', 'Slow (2-5s)', 'Very Slow (>5s)']
                    )
                    perf_dist = valid_search_times['performance_category'].value_counts()
                    
                    fig = px.bar(x=perf_dist.index, y=perf_dist.values,
                                title="Search Response Times")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No valid search time data available")
            else:
                st.info("No performance data available")
    else:
        st.info("No search data available for the selected time period")

with tabs[1]:  # User Feedback
    if not feedback_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 Feedback Types")
            if len(feedback_df) > 0 and 'feedback_type' in feedback_df.columns:
                feedback_types = feedback_df['feedback_type'].value_counts()
                
                if len(feedback_types) > 0:
                    fig = px.bar(x=feedback_types.index, y=feedback_types.values,
                                title="Feedback Categories",
                                labels={'x': 'Feedback Type', 'y': 'Count'})
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No feedback types to display")
            else:
                st.info("No feedback type data available")
        
        with col2:
            st.markdown("#### ⭐ Rating Distribution")
            if 'rating' in feedback_df.columns and not feedback_df['rating'].dropna().empty:
                ratings = feedback_df['rating'].dropna().value_counts().sort_index()
                
                if len(ratings) > 0:
                    fig = px.bar(x=ratings.index, y=ratings.values,
                                title="User Ratings (1-5 Stars)",
                                labels={'x': 'Rating', 'y': 'Count'})
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No rating data available")
            else:
                st.info("No rating data available")

        # Recent feedback table
        st.markdown("#### 💬 Recent User Feedback")
        if not feedback_df.empty:
            display_cols = ['timestamp']
            for col in ['feedback_type', 'message', 'rating', 'contact_info']:
                if col in feedback_df.columns:
                    display_cols.append(col)
            
            recent_feedback = feedback_df.nlargest(10, 'timestamp')[display_cols].copy()
            recent_feedback['timestamp'] = recent_feedback['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            
            # Truncate long messages for display
            if 'message' in recent_feedback.columns:
                recent_feedback['message'] = recent_feedback['message'].str[:100] + '...'
            
            st.dataframe(recent_feedback, use_container_width=True)
        else:
            st.info("No feedback data to display")
    else:
        st.info("No feedback data available for the selected time period")

with tabs[2]:  # Search Patterns
    if not searches_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🕒 Search Activity by Hour")
            if len(searches_df) > 0:
                searches_df['hour'] = searches_df['timestamp'].dt.hour
                hourly_searches = searches_df.groupby('hour').size()
                
                if len(hourly_searches) > 0:
                    fig = px.bar(x=hourly_searches.index, y=hourly_searches.values,
                                title="Searches by Hour of Day",
                                labels={'x': 'Hour', 'y': 'Number of Searches'})
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hourly data available")
            else:
                st.info("No search data available")
        
        with col2:
            st.markdown("#### 📊 Results Distribution")
            if len(searches_df) > 0 and 'results_count' in searches_df.columns:
                result_bins = pd.cut(searches_df['results_count'], 
                                   bins=[0, 1, 10, 50, 100, float('inf')],
                                   labels=['0 results', '1-10', '11-50', '51-100', '100+'])
                result_dist = result_bins.value_counts()
                
                if len(result_dist) > 0:
                    fig = px.pie(values=result_dist.values, names=result_dist.index,
                                title="Search Results Distribution")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No results distribution data available")
            else:
                st.info("No search results data available")

        # Failed searches analysis
        st.markdown("#### ❌ Zero-Result Searches (Need Attention)")
        if metrics['zero_result_searches'] > 0:
            zero_results = searches_df[searches_df['results_count'] == 0]
            failed_queries = zero_results['query'].value_counts().head(10)
            st.write(f"**{len(zero_results)} searches returned no results:**")
            for query, count in failed_queries.items():
                st.write(f"- `{query}` ({count} times)")
        else:
            st.success("🎉 All searches returned results!")
    else:
        st.info("No search pattern data available")

with tabs[3]:  # System Health
    col1, col2, col3 = st.columns(3)
    
    with col1:
        health_score = 100
        if metrics['total_errors'] > 5:
            health_score -= 20
        if metrics['search_success_rate'] < 0.8:
            health_score -= 15
        if metrics['avg_search_time'] > 3:
            health_score -= 10
        if metrics['avg_rating'] < 3:
            health_score -= 10
        
        health_color = "#28a745" if health_score > 80 else "#ffc107" if health_score > 60 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin: 0; color: {health_color};">🏥 {health_score}/100</h3>
            <p style="margin: 0; color: #6c757d;">System Health Score</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        uptime_color = "#28a745" if metrics['avg_search_time'] < 2 else "#ffc107" if metrics['avg_search_time'] < 5 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin: 0; color: {uptime_color};">⏱️ {metrics['avg_search_time']:.1f}s</h3>
            <p style="margin: 0; color: #6c757d;">Avg Search Time</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        user_satisfaction = metrics['avg_rating'] / 5 * 100 if metrics['avg_rating'] > 0 else 0
        satisfaction_color = "#28a745" if user_satisfaction > 70 else "#ffc107" if user_satisfaction > 50 else "#dc3545"
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin: 0; color: {satisfaction_color};">😊 {user_satisfaction:.0f}%</h3>
            <p style="margin: 0; color: #6c757d;">User Satisfaction</p>
        </div>
        """, unsafe_allow_html=True)

    # Error analysis
    if not errors_df.empty:
        st.markdown("#### 🔍 Error Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            if 'error_type' in errors_df.columns:
                error_types = errors_df['error_type'].value_counts()
                if len(error_types) > 0:
                    fig = px.bar(x=error_types.values, y=error_types.index,
                                orientation='h', title="Error Types",
                                labels={'x': 'Count', 'y': 'Error Type'})
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No error types to display")
            else:
                st.info("No error type data available")
        
        with col2:
            st.markdown("**Recent Errors:**")
            display_cols = ['timestamp']
            for col in ['error_type', 'error_message']:
                if col in errors_df.columns:
                    display_cols.append(col)
            
            recent_errors = errors_df.nlargest(5, 'timestamp')[display_cols].copy()
            recent_errors['timestamp'] = recent_errors['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            
            if 'error_message' in recent_errors.columns:
                recent_errors['error_message'] = recent_errors['error_message'].str[:50] + '...'
            
            st.dataframe(recent_errors, use_container_width=True)
    else:
        st.markdown("""
        <div class="success-card">
            <h4 style="margin: 0;">✅ No Recent Errors</h4>
            <p style="margin: 0.5rem 0 0 0;">System running smoothly!</p>
        </div>
        """, unsafe_allow_html=True)

with tabs[4]:  # Raw Data
    st.markdown("#### 📊 Data Export & Raw Access")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Export Search Data"):
            if not searches_df.empty:
                csv = searches_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"search_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No search data to export")
    
    with col2:
        if st.button("📥 Export Feedback Data"):
            if not feedback_df.empty:
                csv = feedback_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"feedback_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No feedback data to export")
    
    with col3:
        if st.button("📥 Export Error Data"):
            if not errors_df.empty:
                csv = errors_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"error_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No error data to export")

    # Raw data viewers
    if st.checkbox("🔍 Show Raw Search Data"):
        st.dataframe(searches_df if not searches_df.empty else pd.DataFrame({"Message": ["No data available"]}))
    
    if st.checkbox("🔍 Show Raw Feedback Data"):
        st.dataframe(feedback_df if not feedback_df.empty else pd.DataFrame({"Message": ["No data available"]}))

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <p><strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
    <strong>Data Range:</strong> Last {time_period} days | 
    <strong>Cache TTL:</strong> 5 minutes</p>
    <p>Council Assistant Admin Dashboard v2.0 | Standalone Mode</p>
</div>
""", unsafe_allow_html=True)