import streamlit as st
import os
import sys
from pathlib import Path
import pandas as pd

# Add project root to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from database.database import DatabaseManager
from agents.orchestrator import BloodLinkOrchestrator
from utils.logger import logger
from frontend.components.sidebar import render_sidebar
from frontend.views.dashboard import render_dashboard
from frontend.views.inventory import render_inventory
from frontend.views.donors import render_donors
from frontend.views.patients import render_patients
from frontend.views.blood_requests import render_blood_requests
from frontend.views.emergency import render_emergency
from frontend.views.assistant import render_assistant
from frontend.views.analytics import render_analytics
from frontend.views.settings import render_settings
from frontend.utils.ui_config import load_custom_css

def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'orchestrator' not in st.session_state:
        try:
            st.session_state.orchestrator = BloodLinkOrchestrator()
            st.session_state.db_manager = DatabaseManager()
            st.session_state.system_status = "Online"
        except Exception as e:
            logger.error(f"Failed to initialize backend components: {e}", exc_info=True)
            st.session_state.system_status = f"Error: {str(e)}"
            st.session_state.orchestrator = None
            st.session_state.db_manager = None

    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
        
        # Validate emergency coordinates on startup
        if st.session_state.db_manager:
            try:
                from frontend.utils.database import fetch_data
                emg_df = fetch_data("SELECT id, event_name, location_city, latitude, longitude FROM EmergencyEvent WHERE is_active = 1")
                for _, row in emg_df.iterrows():
                    missing = []
                    if not row.get('location_city'): missing.append('City')
                    if pd.isna(row.get('latitude')) or float(row.get('latitude', 0)) == 0.0: missing.append('Latitude')
                    if pd.isna(row.get('longitude')) or float(row.get('longitude', 0)) == 0.0: missing.append('Longitude')
                    
                    if missing:
                        logger.warning(f"Incomplete seed data: EmergencyEvent '{row.get('event_name')}' (ID {row.get('id')}) is missing: {', '.join(missing)}")
            except Exception as e:
                logger.error(f"Failed to validate emergency coordinates: {e}")



def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="BloodLink AI",
        page_icon="🩸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply modern UI theme
    load_custom_css()
    
    init_session_state()
    selected_page = render_sidebar()
    
    try:
        if selected_page == "Dashboard":
            render_dashboard()
        elif selected_page == "Inventory":
            render_inventory()
        elif selected_page == "Donors":
            render_donors()
        elif selected_page == "Patients":
            render_patients()
        elif selected_page == "Blood Requests":
            render_blood_requests()
        elif selected_page == "Emergency":
            render_emergency()
        elif selected_page == "Analytics":
            render_analytics()
        elif selected_page == "Settings":
            render_settings()
        elif selected_page == "AI Assistant":
            render_assistant()
        else:
            st.header(selected_page)
            st.write("Module under construction.")
    except Exception as e:
        st.error("An unexpected error occurred while rendering the page.")
        logger.error(f"Page render error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
