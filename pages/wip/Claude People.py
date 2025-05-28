import streamlit as st
import pandas as pd

# Configure page
st.set_page_config(page_title="Person Directory", layout="wide")

# Sample data - replace with your actual data
@st.cache_data
def load_people_data():
    return pd.DataFrame({
        'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown', 'Charlie Wilson'],
        'Department': ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance'],
        'Position': ['Senior Developer', 'Marketing Manager', 'Sales Rep', 'HR Specialist', 'Accountant'],
        'Location': ['New York', 'San Francisco', 'Chicago', 'Boston', 'Seattle'],
        'Years': [5, 3, 7, 2, 4]
    })

# Initialize session state for navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'main'
if 'selected_person' not in st.session_state:
    st.session_state.selected_person = None

def show_main_page():
    """Display the main table with all people"""
    st.title("🏢 Company Directory")
    st.markdown("---")
    
    # Load data
    df = load_people_data()
    
    # Display using Streamlit's dataframe with custom styling
    st.markdown("### 👥 All Personnel")
    
    # Create the table using streamlit components
    for i, (_, row) in enumerate(df.iterrows()):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 3, 2, 1])
            
            with col1:
                if st.button(f"👤 **{row['Name']}**", key=f"person_{i}", use_container_width=True):
                    st.session_state.selected_person = row['Name']
                    st.session_state.current_page = 'person'
                    st.rerun()
            
            with col2:
                st.write(f"**{row['Department']}**")
            
            with col3:
                st.write(row['Position'])
            
            with col4:
                st.write(row['Location'])
            
            with col5:
                st.write(f"{row['Years']} yrs")
        
        # Add a subtle separator
        if i < len(df) - 1:
            st.markdown("<hr style='margin: 5px 0; border: 0.5px solid #e0e0e0;'>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Alternative compact table view
    st.markdown("### 📋 Quick Reference Table")
    
    # Use Streamlit's built-in dataframe display
    st.dataframe(
        df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Department": st.column_config.TextColumn("Department", width="small"),
            "Position": st.column_config.TextColumn("Position", width="medium"), 
            "Location": st.column_config.TextColumn("Location", width="small"),
            "Years": st.column_config.NumberColumn("Experience (Years)", width="small")
        }
    )
    
    # Add selection buttons below the table
    st.markdown("### 🔍 Select a Person:")
    cols = st.columns(3)
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i % 3]:
            if st.button(f"View {row['Name']}", key=f"btn_{i}", use_container_width=True):
                st.session_state.selected_person = row['Name']
                st.session_state.current_page = 'person'
                st.rerun()

def show_person_page():
    """Display individual person page"""
    person_name = st.session_state.selected_person
    df = load_people_data()
    person_data = df[df['Name'] == person_name].iloc[0]
    
    # Back button
    if st.button("← Back to Directory", type="primary"):
        st.session_state.current_page = 'main'
        st.session_state.selected_person = None
        st.rerun()
    
    st.markdown("---")
    
    # Person header
    st.title(f"👤 {person_data['Name']}")
    
    # Person details in columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📊 Quick Info")
        st.info(f"""
        **Department:** {person_data['Department']}
        
        **Position:** {person_data['Position']}
        
        **Location:** {person_data['Location']}
        
        **Experience:** {person_data['Years']} years
        """)
    
    with col2:
        st.markdown("### 📝 Profile Details")
        
        # Expandable sections
        with st.expander("🎯 Role & Responsibilities", expanded=True):
            st.write(f"""
            As a {person_data['Position']} in the {person_data['Department']} department, 
            {person_data['Name']} brings {person_data['Years']} years of valuable experience 
            to our team based in {person_data['Location']}.
            """)
        
        with st.expander("📈 Performance Metrics"):
            # Sample metrics - replace with actual data
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Projects Completed", "23", "3")
            with metric_col2:
                st.metric("Team Rating", "4.8/5", "0.2")
            with metric_col3:
                st.metric("Certifications", "5", "1")
        
        with st.expander("📞 Contact Information"):
            st.write(f"""
            **Email:** {person_data['Name'].lower().replace(' ', '.')}@company.com
            
            **Phone:** +1 (555) 123-4567
            
            **Office:** {person_data['Location']} Office, Floor 3
            """)
    
    # Additional sections
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🏆 Achievements", "📅 Schedule"])
    
    with tab1:
        st.subheader("Performance Analytics")
        # You could add charts here using st.line_chart, st.bar_chart, etc.
        st.info("Analytics dashboard would go here")
    
    with tab2:
        st.subheader("Recent Achievements")
        achievements = [
            "🎯 Completed Q4 2024 objectives ahead of schedule",
            "🏆 Employee of the Month - December 2024",
            "📈 Led team to 15% performance improvement",
            "🎓 Completed Advanced Leadership Training"
        ]
        for achievement in achievements:
            st.write(f"• {achievement}")
    
    with tab3:
        st.subheader("Upcoming Schedule")
        st.info("Calendar integration would go here")

# Main app logic
def main():
    # Navigation logic
    if st.session_state.current_page == 'main':
        show_main_page()
    elif st.session_state.current_page == 'person':
        show_person_page()

if __name__ == "__main__":
    main()