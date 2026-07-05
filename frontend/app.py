"""
Streamlit frontend application for BloodLink AI.
"""

import streamlit as st

def main():
    # Configure the page
    st.set_page_config(
        page_title="BloodLink AI",
        page_icon="🩸",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    pages = [
        "Home",
        "Request Blood",
        "Donate Blood",
        "Emergency Mode",
        "Analytics",
        "Hospital Dashboard",
        "Admin Dashboard"
    ]
    
    selection = st.sidebar.radio("Go to", pages)

    # Main Header
    st.title("BloodLink AI 🩸")
    st.subheader("AI Powered Blood Supply Management")
    st.divider()

    # Route to the selected page
    if selection == "Home":
        st.header("Home")
        st.info("Placeholder for the Home page.")
    
    elif selection == "Request Blood":
        st.header("Request Blood")
        st.info("Placeholder for the Request Blood page.")
    
    elif selection == "Donate Blood":
        st.header("Donate Blood")
        st.info("Placeholder for the Donate Blood page.")
    
    elif selection == "Emergency Mode":
        st.header("Emergency Mode")
        st.warning("Placeholder for the Emergency Mode page.")
    
    elif selection == "Analytics":
        st.header("Analytics")
        st.info("Placeholder for the Analytics page.")
    
    elif selection == "Hospital Dashboard":
        st.header("Hospital Dashboard")
        st.info("Placeholder for the Hospital Dashboard page.")
    
    elif selection == "Admin Dashboard":
        st.header("Admin Dashboard")
        st.info("Placeholder for the Admin Dashboard page.")

if __name__ == "__main__":
    main()
