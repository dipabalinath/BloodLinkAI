import streamlit as st
import pandas as pd
import plotly.express as px
from utils.logger import logger
from frontend.utils.database import (
    get_inventory_by_group,
    get_donor_group_distribution,
    get_donors_by_city,
    get_monthly_donations,
    get_requests_by_status,
    get_emergency_trends,
    get_expiring_aggregate,
    get_ai_decisions
)

def render_analytics():
    """Render the Analytics Dashboard page."""
    st.header("📈 Advanced Analytics")
    st.write("Visualize system-wide data, inventory trends, and AI performance metrics.")

    db = st.session_state.get('db_manager')
    if not db:
        st.error("Database connection not initialized.")
        return

    try:
        # 1. Blood Inventory & Group Distribution
        st.subheader("Inventory Metrics")
        col1, col2 = st.columns(2)
        
        with col1:
            inv_df = get_inventory_by_group()
            if not inv_df.empty and not inv_df['total_units'].isna().all():
                fig1 = px.bar(inv_df, x='blood_group', y='total_units', title="Current Inventory by Blood Group", color='blood_group', color_discrete_sequence=['#C62828', '#1565C0', '#2E7D32', '#F9A825', '#D32F2F'])
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No inventory data.")
                
        with col2:
            # Group distribution across donors
            donor_bg_df = get_donor_group_distribution()
            if not donor_bg_df.empty:
                fig2 = px.pie(donor_bg_df, names='blood_group', values='count', title="Donor Blood Group Distribution", hole=0.3, color_discrete_sequence=['#1565C0', '#C62828', '#2E7D32', '#F9A825'])
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No donor data.")
                
        st.markdown("---")
        
        # 2. Donor Registrations & Monthly Donations
        st.subheader("Donor & Donation Trends")
        col3, col4 = st.columns(2)
        
        with col3:
            # Donor registrations by city
            donor_city_df = get_donors_by_city()
            if not donor_city_df.empty:
                fig3 = px.bar(donor_city_df, x='city', y='count', title="Donor Base by City", color='city', color_discrete_sequence=['#2E7D32', '#1565C0', '#C62828'])
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No donor city data.")
                
        with col4:
            # Monthly donations (using donation_date)
            don_df = get_monthly_donations()
            if not don_df.empty:
                fig4 = px.line(don_df, x='month', y='total_vol', title="Monthly Donation Volume (mL)", markers=True, color_discrete_sequence=['#C62828'])
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("No donation history data.")
                
        st.markdown("---")
        
        # 3. Blood Requests & Emergency Trends
        st.subheader("Requests & Emergencies")
        col5, col6 = st.columns(2)
        
        with col5:
            # Blood Requests by Status
            req_df = get_requests_by_status()
            if not req_df.empty:
                fig5 = px.pie(req_df, names='status', values='count', title="Blood Requests by Status", color_discrete_sequence=['#F9A825', '#1565C0', '#2E7D32', '#D32F2F'])
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("No request data.")
                
        with col6:
            # Emergency Trends
            emerg_df = get_emergency_trends()
            if not emerg_df.empty:
                fig6 = px.bar(emerg_df, x='month', y='count', color='severity_level', title="Emergency Trends by Severity", barmode='stack', color_discrete_map={'CRITICAL': '#D32F2F', 'HIGH': '#C62828', 'MEDIUM': '#F9A825', 'LOW': '#1565C0'})
                st.plotly_chart(fig6, use_container_width=True)
            else:
                st.info("No emergency data.")
                
        st.markdown("---")
        
        # 4. Expiring Inventory & AI Decisions
        st.subheader("Operational & AI Metrics")
        col7, col8 = st.columns(2)
        
        with col7:
            # Expiring within next 14 days
            exp_df = get_expiring_aggregate(days=14)
            if not exp_df.empty and not exp_df['units'].isna().all():
                fig7 = px.bar(exp_df, x='expiry_date', y='units', title="Units Expiring Soon (Next 14 Days)", color_discrete_sequence=['#D32F2F'])
                st.plotly_chart(fig7, use_container_width=True)
            else:
                st.success("No inventory expiring within 14 days.")
                
        with col8:
            # AI Decisions (AgentDecisionLog)
            ai_df = get_ai_decisions()
            if not ai_df.empty:
                fig8 = px.pie(ai_df, names='agent_name', values='count', title="AI Interventions by Agent", hole=0.4, color_discrete_sequence=['#1565C0', '#2E7D32', '#C62828', '#F9A825'])
                st.plotly_chart(fig8, use_container_width=True)
            else:
                st.info("No AI decision logs found. Trigger AI tasks to generate logs.")
                
    except Exception as e:
        st.error(f"Failed to render analytics: {e}")
        logger.error(f"Analytics rendering error: {e}", exc_info=True)
