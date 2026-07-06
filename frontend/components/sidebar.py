import streamlit as st
from pathlib import Path

def render_sidebar() -> str:
    """
    Render the sidebar navigation for BloodLink AI.
    Returns the name of the selected page.
    """
    with st.sidebar:
        # Load logo if available
        logo_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
        else:
            st.title("🩸 BloodLink AI")
            
        st.markdown("---")
        
        pages = {
            "🏠 Dashboard": "Dashboard",
            "🩸 Inventory": "Inventory",
            "👤 Donors": "Donors",
            "🏥 Patients": "Patients",
            "📄 Blood Requests": "Blood Requests",
            "🚨 Emergency": "Emergency",
            "🤖 AI Assistant": "AI Assistant",
            "📊 Analytics": "Analytics",
            "⚙ Settings": "Settings"
        }
        
        current_page = st.session_state.get('current_page', 'Dashboard')
        
        for display_name, internal_name in pages.items():
            if st.button(
                display_name, 
                use_container_width=True, 
                type="primary" if current_page == internal_name else "secondary"
            ):
                st.session_state.current_page = internal_name
                st.rerun()

        st.markdown("---")
        st.markdown("### System Status")
        if "Error" in st.session_state.get('system_status', ''):
            st.error(st.session_state.get('system_status', 'Unknown Error'))
        else:
            st.success(st.session_state.get('system_status', 'Online'))
            
        st.markdown("---")
        st.markdown(
            "<div style='font-size: 12px; color: gray; text-align: center;'>"
            "<b>BloodLink AI</b><br/>"
            "AI Powered Blood Supply Management<br/>"
            "SQLite + MCP + Google ADK<br/>"
            "Version 1.0"
            "</div>",
            unsafe_allow_html=True
        )
            
    return st.session_state.get('current_page', 'Dashboard')
