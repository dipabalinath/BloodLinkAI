import streamlit as st
from config.settings import settings
from mcp_server.registry import registry

def render_settings():
    """Render the System Settings page."""
    st.header("⚙️ System Settings")
    st.write("View and verify the internal configuration and status of BloodLink AI.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Environment Configuration")
        st.write(f"**Application Env:** `{settings.APP_ENV}`")
        st.write(f"**Log Level:** `{settings.LOG_LEVEL}`")
        st.write(f"**Database Path:** `{settings.DATABASE_URL}`")
        st.write(f"**Debug Mode:** `{'Enabled' if settings.DEBUG else 'Disabled'}`")

    with col2:
        st.subheader("AI Configuration")
        st.write(f"**AI Model:** `{settings.MODEL_NAME}`")
        
        if settings.USE_MOCK_AI:
            st.warning("⚠️ **Mock AI Mode is ACTIVE** (LLM is bypassed for deterministic testing)")
        else:
            st.success("✅ **Live AI Mode is ACTIVE** (Connected to Gemini API)")
            
        st.write(f"**Google API Key:** `{'Configured' if settings.GOOGLE_API_KEY else 'Missing'}`")

    st.markdown("---")
    
    st.subheader("Component Diagnostics")
    
    if st.button("Run System Diagnostics", type="primary"):
        with st.spinner("Testing internal connections..."):
            
            # Database Check
            db = st.session_state.get('db_manager')
            if db:
                try:
                    with db.connect() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1")
                        st.success("✅ **SQLite Database:** Connection established and querying successfully.")
                except Exception as e:
                    st.error(f"❌ **SQLite Database:** Connection Failed ({e})")
            else:
                st.error("❌ **SQLite Database:** Manager not initialized in session.")

            # Orchestrator Check
            orchestrator = st.session_state.get('orchestrator')
            if orchestrator and len(orchestrator.agents) > 0:
                st.success(f"✅ **AI Orchestrator:** Online ({len(orchestrator.agents)} specialized agents loaded).")
            else:
                st.error("❌ **AI Orchestrator:** Failed to load specialized agents.")
                
            # MCP Status
            try:
                tools_count = len(registry.tools)
                if tools_count > 0:
                    st.success(f"✅ **MCP Server Registry:** Online ({tools_count} native tools registered).")
                else:
                    st.warning("⚠️ **MCP Server Registry:** Running, but 0 tools are registered.")
            except Exception as e:
                st.error(f"❌ **MCP Server Registry:** Failed ({e})")
