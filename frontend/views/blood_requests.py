import streamlit as st
import pandas as pd
import json
from datetime import datetime
from frontend.utils.database import get_all_requests, get_blood_requests_metrics, update_request_status, get_request_details, get_active_reservations

def format_req_status(status):
    if not isinstance(status, str): return status
    s = status.lower()
    if s == 'pending': return '🟡 Pending'
    if s == 'partially fulfilled': return '🟠 Partially Fulfilled'
    if s == 'fulfilled': return '🟢 Fulfilled'
    if s == 'cancelled': return '🔴 Cancelled'
    return status

def render_blood_requests():
    """Render the Blood Requests & Allocation dashboard."""
    st.header("🚑 Blood Requests & Allocation Dashboard")
    st.write("Operational workspace for monitoring, allocating, and fulfilling blood requests.")

    db = st.session_state.get('db_manager')
    orchestrator = st.session_state.get('orchestrator')
    
    if not db or not orchestrator:
        st.error("System components not initialized.")
        return
        
    # Initialize session state for selected request
    if 'selected_req_id' not in st.session_state:
        st.session_state.selected_req_id = None
        
    # Display any pending notifications from a previous run
    if 'req_notification' in st.session_state and st.session_state.req_notification:
        notif = st.session_state.req_notification
        if notif.startswith("⚠"):
            st.warning(notif)
        else:
            st.success(notif)
        st.session_state.req_notification = None

    # 1. Dashboard Summary KPIs
    metrics = get_blood_requests_metrics()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🟡 Pending Requests", metrics.get("Pending Requests", 0))
    col2.metric("🔴 Urgent Requests", metrics.get("Urgent Requests", 0))
    col3.metric("🔵 Reserved Units", metrics.get("Reserved Units", 0))
    col4.metric("🟢 Fulfilled Today", metrics.get("Fulfilled Today", 0))
    col5.metric("❌ Cancelled", metrics.get("Cancelled Requests", 0))
    
    st.markdown("---")

    # 2. Active Request Queue & Filters
    st.subheader("Active Request Queue")
    
    # Filters
    f_col1, f_col2, f_col3 = st.columns(3)
    filter_status = f_col1.selectbox("Filter by Status", ["All", "Pending", "Partially Fulfilled", "Fulfilled", "Cancelled"])
    filter_bg = f_col2.selectbox("Filter by Blood Group", ["All", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
    filter_priority = f_col3.selectbox("Filter by Priority", ["All", "🔴 Critical (Immediate)", "🟠 High (Urgent)", "🟡 Medium (Scheduled)", "🟢 Low (Elective)", "⚪ Not Yet Assessed"])

    req_df = get_all_requests(limit=100)
    
    if not req_df.empty:
        # Apply Filters
        if filter_status != "All":
            req_df = req_df[req_df['Current Request Status'].str.lower() == filter_status.lower()]
        if filter_bg != "All":
            req_df = req_df[req_df['Blood Group'] == filter_bg]
        if filter_priority != "All":
            req_df = req_df[req_df['Priority'] == filter_priority]

        if 'Date Requested' in req_df.columns:
            req_df['Date Requested'] = pd.to_datetime(req_df['Date Requested'], errors='coerce').dt.strftime('%d %b %Y %I:%M %p')
            
        if 'Current Request Status' in req_df.columns:
            req_df['Current Request Status'] = req_df['Current Request Status'].apply(format_req_status)
            
        # Display Queue
        st.dataframe(req_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 3. Action Panel & AI Allocation
        st.subheader("Manage Request")
        
        with st.expander("ℹ️ Clinical Status vs Allocation Status"):
            st.markdown("""
**Clinical Request Status** (Patient-centric):
• 🟡 **Pending**: Request created, no blood issued yet.
• 🟠 **Partially Fulfilled**: Some requested units issued.
• 🟢 **Fulfilled**: All requested units issued.
• 🔴 **Cancelled**: Request cancelled by clinician.

**Reservation Status** (Inventory-centric):
• 🟡 **Pending**: Awaiting inventory allocation.
• 🟢 **Active**: Units reserved for this request.
• 🔵 **Issued**: Units permanently issued.
            """)
        
        col_select, col_actions = st.columns([1, 2])
        
        with col_select:
            # Request Selection
            request_ids = req_df['Request ID'].tolist()
            if request_ids:
                default_idx = 0
                if st.session_state.selected_req_id in request_ids:
                    default_idx = request_ids.index(st.session_state.selected_req_id)
                selected_req_id = st.selectbox("Select Request ID to Manage", request_ids, index=default_idx)
                st.session_state.selected_req_id = selected_req_id
            else:
                selected_req_id = None
                st.session_state.selected_req_id = None
                st.info("No requests match the current filters.")
                
        if selected_req_id:
            req_details = get_request_details(selected_req_id)
            if not req_details:
                st.error("Could not fetch request details.")
                return
                
            current_status = req_details.get("status", "Unknown")
            
            with col_actions:
                st.write(f"**Patient:** {req_details.get('patient_name')} | **Facility:** {req_details.get('facility_name')}")
                st.write(f"**Request:** {req_details.get('requested_units')} units of {req_details.get('blood_group')} {req_details.get('component_type')}")
                st.write(f"**Status:** {format_req_status(current_status)}")
                
                # Clinical Workflow timeline
                workflow = ["Pending", "Partially Fulfilled", "Fulfilled"]
                try:
                    curr_idx = workflow.index(current_status)
                except ValueError:
                    curr_idx = -1
                    
                st.progress((curr_idx + 1) / len(workflow) if curr_idx >= 0 else 0, text=f"Clinical Request Stage: {current_status}")
                
                # Retrieve reservation status for visual indicator
                res_df = get_active_reservations()
                res_status_text = "No Active Reservation"
                if not res_df.empty:
                    req_res_df = res_df[res_df["Blood Request ID"] == selected_req_id]
                    if not req_res_df.empty:
                        r_status = req_res_df.iloc[0]["Status"]
                        res_status_text = f"Reservation Status: {r_status}"
                        
                st.info(f"📦 {res_status_text}")
                
                # Action Buttons
                btn_cols = st.columns(3)
                
                # If status == Cancelled, disable all. If Partially Fulfilled, only allow Mark Fulfilled.
                can_partial = current_status not in ["Partially Fulfilled", "Fulfilled", "Cancelled"]
                can_fulfill = current_status not in ["Fulfilled", "Cancelled"]
                can_cancel = current_status not in ["Fulfilled", "Cancelled"]
                
                if btn_cols[0].button("🟠 Mark Partially Fulfilled", key=f"partial_{selected_req_id}", disabled=not can_partial, use_container_width=True):
                    import logging
                    from frontend.utils.database import fetch_data
                    logging.info(f"Updating request {selected_req_id} to Partially Fulfilled")
                    update_request_status(selected_req_id, "Partially Fulfilled")
                    st.session_state.req_notification = "✅ Request updated to Partially Fulfilled."
                    logging.info("Reloading request queue...")
                    logging.info("Reloading dashboard metrics...")
                    logging.info("Reloading request details...")
                    fetch_data.clear()
                    st.rerun()
                    
                if btn_cols[1].button("🟢 Mark Fulfilled", key=f"full_{selected_req_id}", disabled=not can_fulfill, type="primary", use_container_width=True):
                    import logging
                    from frontend.utils.database import fetch_data
                    logging.info(f"Updating request {selected_req_id} to Fulfilled")
                    update_request_status(selected_req_id, "Fulfilled")
                    st.session_state.req_notification = "✅ Request marked as Fulfilled."
                    logging.info("Reloading request queue...")
                    logging.info("Reloading dashboard metrics...")
                    logging.info("Reloading request details...")
                    fetch_data.clear()
                    st.rerun()
                    
                if btn_cols[2].button("🔴 Cancel Request", key=f"cancel_{selected_req_id}", disabled=not can_cancel, use_container_width=True):
                    import logging
                    from frontend.utils.database import fetch_data
                    logging.info(f"Updating request {selected_req_id} to Cancelled")
                    update_request_status(selected_req_id, "Cancelled")
                    st.session_state.req_notification = "⚠ Request Cancelled."
                    logging.info("Reloading request queue...")
                    logging.info("Reloading dashboard metrics...")
                    logging.info("Reloading request details...")
                    fetch_data.clear()
                    st.rerun()
            
            st.markdown("---")
            
            # AI Allocation Assistant Panel
            st.subheader("🤖 AI Allocation Assistant")
            
            if st.button("🤖 Generate AI Allocation Recommendation", type="primary"):
                with st.spinner("Analyzing inventory and generating recommendation..."):
                    try:
                        # Fetch context
                        context_params = {
                            "request_id": selected_req_id,
                            "blood_group": req_details.get("blood_group"),
                            "component_type": req_details.get("component_type"),
                            "latitude": req_details.get("latitude", 0.0),
                            "longitude": req_details.get("longitude", 0.0),
                            "required_units": req_details.get("requested_units"),
                            "facility_name": req_details.get("facility_name"),
                            "requested_priority": req_details.get("requested_priority", "medium")
                        }
                        
                        # Call orchestrator manually or specifically Recommendation & Notification
                        rec_agent = orchestrator.agents.get('recommendation')
                        notif_agent = orchestrator.agents.get('notification')
                        
                        rec_res = rec_agent.execute(
                            user_request=f"Recommend inventory for request {selected_req_id}",
                            blood_group=context_params["blood_group"],
                            component_type=context_params["component_type"],
                            latitude=context_params["latitude"],
                            longitude=context_params["longitude"],
                            required_units=context_params["required_units"],
                            context_params=context_params
                        )
                        
                        notif_res = notif_agent.execute(
                            user_request=f"Notify donors for request {selected_req_id}",
                            blood_group=context_params["blood_group"],
                            urgency=str(context_params["requested_priority"]).lower(),
                            location=context_params["facility_name"],
                            inventory_available=False,
                            context_params=context_params
                        )
                        
                        # Display Results
                        st.info(f"**Allocation Recommendation:** {rec_res.get('recommendation', 'No recommendation generated.')}")
                        
                        if notif_res.get("notification_required"):
                            st.warning(f"**Donor Outreach Required:** {notif_res.get('message', 'Outreach needed.')}")
                        else:
                            st.success("**Donor Outreach:** Not required, sufficient inventory available.")
                            
                    except Exception as e:
                        st.error(f"Error generating AI recommendation: {e}")
            
            st.markdown("---")
            
            # 5. Reservation Panel
            st.subheader("Active Reservations")
            res_df = get_active_reservations()
            if not res_df.empty:
                # Filter for this request
                req_res_df = res_df[res_df["Blood Request ID"] == selected_req_id]
                if not req_res_df.empty:
                    st.dataframe(req_res_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No active reservations for this request.")
            else:
                st.info("No active reservations in the system.")
                
    else:
        st.info("No blood requests found in the system. Create requests from the Patient Management page.")

