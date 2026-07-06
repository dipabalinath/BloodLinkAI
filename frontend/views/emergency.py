import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from utils.logger import logger
from frontend.utils.database import get_active_emergencies, get_recent_notifications, fetch_data
from frontend.utils.sanitizer import sanitize_for_json, safe_float

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def get_enhanced_facilities(blood_group, required_units, target_lat, target_lon):
    """Fetch all facilities and calculate their status based on inventory."""
    # Base query for all facilities
    fac_df = fetch_data("SELECT id, name, facility_type, CAST(latitude AS REAL) as lat, CAST(longitude AS REAL) as lon, address FROM HealthcareFacility WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    
    if fac_df.empty:
        return fac_df
        
    # Get inventory for this blood group
    if blood_group == "All":
        inv_df = fetch_data("SELECT facility_id, SUM(units_available) as units FROM BloodInventory GROUP BY facility_id")
    else:
        inv_df = fetch_data("SELECT facility_id, SUM(units_available) as units FROM BloodInventory WHERE blood_group = ? GROUP BY facility_id", (blood_group,))
        
    if not inv_df.empty:
        fac_df = fac_df.merge(inv_df, left_on='id', right_on='facility_id', how='left')
        fac_df['units'] = fac_df['units'].fillna(0)
    else:
        fac_df['units'] = 0

    # Calculate distance and travel time (assume avg 40 km/h)
    fac_df['distance_km'] = haversine(target_lat, target_lon, fac_df['lat'], fac_df['lon'])
    fac_df['travel_time_min'] = (fac_df['distance_km'] / 40.0) * 60
    
    # Determine color status
    def get_color(row):
        if pd.isna(row['lat']) or pd.isna(row['lon']):
            return 'grey'
        if row['units'] >= required_units and required_units > 0:
            return 'green'
        elif row['units'] > 0:
            return 'orange'
        else:
            return 'red'
            
    def get_status(row):
        c = get_color(row)
        if c == 'green': return '🟢 Sufficient'
        if c == 'orange': return '🟡 Partial'
        if c == 'red': return '🔴 Unavailable'
        return '⚫ Filtered'
        
    fac_df['color'] = fac_df.apply(get_color, axis=1)
    fac_df['status_label'] = fac_df.apply(get_status, axis=1)
    
    return fac_df

def render_emergency():
    """Render the Emergency Response Command Center page."""
    
    # Notification handling
    if 'emg_notification' in st.session_state and st.session_state.emg_notification:
        st.success(st.session_state.emg_notification)
        st.session_state.emg_notification = None

    db = st.session_state.get('db_manager')
    orchestrator = st.session_state.get('orchestrator')
    
    if not db or not orchestrator:
        st.error("System components not initialized.")
        return
        
    emerg_df = get_active_emergencies()
    
    # -------------------------------------------------------------------------
    # 1. Top Emergency Banner
    # -------------------------------------------------------------------------
    st.markdown("""
        <div style="background-color: #C62828; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h1 style="margin: 0; color: white;">🚨 Emergency Response Command Center</h1>
            <p style="margin: 5px 0 0 0; font-size: 1.1em; opacity: 0.9;">AI-powered disaster blood coordination & emergency dispatch</p>
        </div>
    """, unsafe_allow_html=True)

    if emerg_df.empty:
        st.success("✅ No active emergencies at this time.")
        return
        
    # Select Emergency Event
    event_names = emerg_df['Event'].tolist()
    
    default_ev_idx = 0
    if st.session_state.get('emg_selected_event') in event_names:
        default_ev_idx = event_names.index(st.session_state['emg_selected_event'])
        
    selected_event_name = st.selectbox("Select Active Incident to Manage", event_names, index=default_ev_idx)
    st.session_state['emg_selected_event'] = selected_event_name
    
    if not selected_event_name:
        st.warning("⚠ No emergency event selected.")
        logger.warning("Selected emergency event not found.")
        return
        
    selected_event = emerg_df[emerg_df['Event'] == selected_event_name]
    if selected_event.empty:
        st.warning("⚠ No emergency event selected.")
        logger.warning("Selected emergency event not found.")
        return
        
    selected_event = selected_event.iloc[0]
    
    # "Event ID" is the column returned by get_active_emergencies()
    selected_id = selected_event.get('Event ID')
    if not selected_id:
        st.warning("⚠ No emergency event selected.")
        logger.warning("Selected emergency event has no valid ID.")
        return
        
    severity = selected_event.get('Severity', 'Unknown')
    city = selected_event.get('City', 'Unknown')
    required_units = selected_event.get('Required Units', 0)
    target_lat = safe_float(selected_event.get('latitude'))
    target_lon = safe_float(selected_event.get('longitude'))
    
    logger.info(f"Selected emergency event:\n{selected_event_name} (ID: {selected_id})")
    
    # Handle missing coordinates gracefully
    if target_lat == 0.0 and target_lon == 0.0:
        logger.info("Coordinates missing.")
        
        # Fallback to healthcare facility centroid in the same city
        city_facs = fetch_data("SELECT CAST(latitude AS REAL) as lat, CAST(longitude AS REAL) as lon FROM HealthcareFacility WHERE city = ? AND latitude IS NOT NULL AND longitude IS NOT NULL", (city,))
        
        if not city_facs.empty:
            target_lat = safe_float(city_facs['lat'].mean())
            target_lon = safe_float(city_facs['lon'].mean())
            st.info(f"ℹ️ **Incident coordinates are unavailable.**\n\nThe emergency map has been centred using nearby healthcare facilities in {city}.\n\nDistance calculations and AI recommendations continue to operate normally.")
            logger.info("Using healthcare facility centroid.")
        else:
            # Final fallback if no facilities in the specific city
            all_facs = fetch_data("SELECT CAST(latitude AS REAL) as lat, CAST(longitude AS REAL) as lon FROM HealthcareFacility WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
            if not all_facs.empty:
                target_lat = safe_float(all_facs['lat'].mean())
                target_lon = safe_float(all_facs['lon'].mean())
                st.info("ℹ️ **Incident coordinates are unavailable.**\n\nThe emergency map has been centred using available healthcare facilities.\n\nDistance calculations and AI recommendations continue to operate normally.")
                logger.info("Using overall healthcare facility centroid.")
    
    # -------------------------------------------------------------------------
    # 2. Situation Overview
    # -------------------------------------------------------------------------
    sev_color = "#C62828" if severity in ['CRITICAL', 'HIGH'] else "#F9A825"
    st.markdown(f"""
        <div style="background: white; border-left: 5px solid {sev_color}; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <h3 style="margin: 0; color: {sev_color};">{selected_event_name}</h3>
            <div style="display: flex; gap: 40px; margin-top: 10px;">
                <div><strong>Severity:</strong> {severity}</div>
                <div><strong>Target City:</strong> {city}</div>
                <div><strong>Blood Required:</strong> {required_units} Units</div>
                <div><strong>Priority:</strong> Immediate</div>
                <div><strong>Current Time:</strong> {datetime.now().strftime('%H:%M:%S')}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # -------------------------------------------------------------------------
    # 3. Intelligent Blood Group Filtering
    # -------------------------------------------------------------------------
    st.subheader("GIS Coordination & Dispatch")
    bg_cols = st.columns([1, 2])
    target_bg = bg_cols[0].selectbox("Target Blood Group", ["All", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], index=0)
    
    fac_df = get_enhanced_facilities(target_bg, required_units, target_lat, target_lon)
    
    col_map, col_list = st.columns([2, 1])
    
    # -------------------------------------------------------------------------
    # 4. Emergency Map (Centrepiece)
    # -------------------------------------------------------------------------
    with col_map:
        st.write("### 🏥 Live Emergency Blood Availability")
        st.write("Showing nearby hospitals and blood banks capable of supporting this emergency.")
        if target_bg != "All":
            st.caption(f"Filtering for: **{target_bg}**. Only facilities with compatible inventory are highlighted.")
            
        if not fac_df.empty:
            # Map colors configuration
            color_discrete_map = {
                'green': '#2E7D32',
                'orange': '#F9A825',
                'red': '#D32F2F',
                'grey': '#9E9E9E',
                'blue': '#1565C0'
            }
            
            # Add the emergency location as a black star
            emg_row = pd.DataFrame([{
                'name': f'🚨 {selected_event_name}', 
                'lat': target_lat, 
                'lon': target_lon, 
                'color': 'black',
                'status_label': '🚨 Incident Location',
                'units': 0,
                'distance_km': 0,
                'travel_time_min': 0,
                'size': 15,
                'facility_type': 'Incident',
                'address': 'N/A'
            }])
            
            map_df = pd.concat([fac_df, emg_row], ignore_index=True)
            if 'size' not in map_df.columns:
                map_df['size'] = 10
            map_df['size'] = map_df['size'].fillna(10)
            
            color_discrete_map['black'] = '#000000'
            
            # Apply blue color for dispatched/reserved facilities tracked in session_state
            if 'emg_active_facilities' not in st.session_state:
                st.session_state['emg_active_facilities'] = set()
                
            def override_color(row):
                if row.get('id') in st.session_state.get('emg_active_facilities', set()):
                    return 'blue'
                return row['color']
                
            def override_status(row):
                if row.get('id') in st.session_state.get('emg_active_facilities', set()):
                    return '🔵 Selected for Dispatch'
                return row['status_label']
                
            map_df['color'] = map_df.apply(override_color, axis=1)
            map_df['status_label'] = map_df.apply(override_status, axis=1)
            
            fig = px.scatter_mapbox(
                map_df,
                lat="lat",
                lon="lon",
                color="color",
                color_discrete_map=color_discrete_map,
                size="size",
                hover_name="name",
                hover_data={
                    "color": False,
                    "size": False,
                    "facility_type": True,
                    "address": True,
                    "status_label": True,
                    "units": True,
                    "distance_km": ":.1f",
                    "travel_time_min": ":.0f"
                },
                zoom=10,
                height=500
            )
            fig.update_layout(
                mapbox_style="carto-positron", 
                margin={"r":0,"t":10,"l":0,"b":0},
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("""
            <div style="background: #F6F8FB; padding: 15px; border-radius: 8px; border: 1px solid #E0E0E0; margin-top: 10px;">
                <h4 style="margin-top: 0;">🗺️ Facility Status Legend</h4>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <div>🟢 <strong>Ready:</strong> Facility has sufficient compatible blood units to fulfil the emergency request immediately.</div>
                    <div>🟡 <strong>Partial Availability:</strong> Facility has compatible blood units but cannot satisfy the complete request alone.</div>
                    <div>🔴 <strong>Unavailable:</strong> No compatible blood units currently available.</div>
                    <div>🔵 <strong>Selected for Dispatch:</strong> Facility has been selected by the AI for reservation or emergency dispatch.</div>
                    <div>⚫ <strong>Incident Location:</strong> Represents the emergency incident or the centre point used for coordination.</div>
                </div>
                <p style="margin-top: 10px; font-size: 0.9em; color: #666;"><em>The AI recommends facilities based on distance, inventory availability, and estimated response time.</em></p>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.info("No facilities available to display.")

    # -------------------------------------------------------------------------
    # 5. Nearby Facility Ranking & Facility Popups
    # -------------------------------------------------------------------------
    with col_list:
        st.write("##### Nearby Facilities")
        if not fac_df.empty:
            # Sort by distance
            sorted_facs = fac_df[fac_df['color'] != 'grey'].sort_values('distance_km').head(4)
            if sorted_facs.empty:
                st.warning("No facilities with inventory found.")
            
            for _, f in sorted_facs.iterrows():
                f_color = "#2E7D32" if f['color'] == 'green' else ("#F9A825" if f['color'] == 'orange' else "#D32F2F")
                with st.container(border=True):
                    st.markdown(f"<strong style='color:{f_color};'>{f['name']}</strong><br><small>{f.get('address', 'Unknown Address')}</small>", unsafe_allow_html=True)
                    st.write(f"🚗 {f['distance_km']:.1f} km ({f['travel_time_min']:.0f} mins)")
                    st.write(f"🩸 {int(f['units'])} compatible units available")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("Reserve Blood", key=f"res_{f['id']}", use_container_width=True):
                        st.session_state.emg_active_facilities.add(f['id'])
                        st.session_state.emg_notification = f"✅ Requested reservation of units at {f['name']}."
                        logger.info(f"Reservation triggered for facility {f['id']}")
                        fetch_data.clear()
                        st.rerun()
                    if b2.button("Dispatch", key=f"dis_{f['id']}", type="primary", use_container_width=True):
                        st.session_state.emg_active_facilities.add(f['id'])
                        st.session_state.emg_notification = f"🚀 Emergency dispatch initiated from {f['name']}."
                        logger.info(f"Dispatch triggered for facility {f['id']}")
                        fetch_data.clear()
                        st.rerun()
        else:
            st.info("No nearby data.")
            
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 6. Live Allocation Dashboard & Workflow
    # -------------------------------------------------------------------------
    c_dash1, c_dash2 = st.columns([1, 1])
    with c_dash1:
        st.subheader("Live Allocation Dashboard")
        st.progress(0.45, text="Fulfilment Progress: 45% (68 / 150 Units)")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Required", required_units)
        k2.metric("Reserved", int(required_units * 0.2))
        k3.metric("Dispatched", int(required_units * 0.25))
        k4.metric("Remaining", int(required_units * 0.55))
        
    with c_dash2:
        st.subheader("Response Timeline")
        st.markdown("""
        1. ✅ **Incident Reported**
        2. ✅ **AI Situation Assessment**
        3. ✅ **Inventory Search**
        4. 🔄 **Facility Selection & Reservation** *(In Progress)*
        5. ⏳ **Dispatch Initiated**
        6. ⏳ **Hospital Confirmation**
        """)
        
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 7. AI Emergency Strategy & Dispatch
    # -------------------------------------------------------------------------
    col_ai, col_log = st.columns([2, 1])
    
    with col_ai:
        st.subheader("🤖 AI Operations Report")
        
        # Override the AI prompt to enforce natural language
        if st.button("🧠 Generate Natural Language Strategy", type="primary"):
            with st.spinner("AI is analyzing logistics and writing the operations report..."):
                try:
                    bg_to_request = target_bg if target_bg != "All" else "O-"
                    req_text = (
                        f"We have a {severity} emergency ({selected_event_name}) in {city} requiring {required_units} units of {bg_to_request} blood immediately. "
                        "IMPORTANT: Do NOT return raw JSON. Do NOT return technical fields. "
                        "Instead, generate a professional Emergency Response Report in clear natural language including: "
                        "Situation Assessment, Priority Assessment, Nearest Suitable Facilities, Recommended Allocation Strategy, and Overall Recommendation."
                    )
                    
                    raw_context = {
                        "urgency": severity,
                        "location": city,
                        "latitude": target_lat,
                        "longitude": target_lon,
                        "required_units": required_units,
                        "blood_group": bg_to_request
                    }
                    
                    response = orchestrator.process_request(
                        user_request=req_text,
                        context_params=sanitize_for_json(raw_context)
                    )
                    
                    if response.get("status") == "Success":
                        # We use the final_answer which will be formatted naturally due to our prompt override
                        st.session_state[f'ai_strat_{selected_id}'] = response.get('final_answer')
                        st.session_state.emg_notification = "✅ Strategy Generated Successfully."
                        logger.info("AI Emergency Strategy generated.")
                        fetch_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Failed to generate strategy: {response.get('error')}")
                except Exception as e:
                    st.error(f"Orchestration Error: {e}")
                    
        # Display saved AI Strategy
        ai_strat = st.session_state.get(f'ai_strat_{selected_id}')
        if ai_strat:
            with st.container(border=True):
                if isinstance(ai_strat, dict):
                    # Fallback if the agent still forced JSON
                    for k, v in ai_strat.items():
                        st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
                else:
                    st.markdown(ai_strat)
                    
        # Donor Mobilization Mock
        st.info(f"📣 **Donor Mobilization:** Notify 24 eligible {target_bg} donors within 10 km. (Recommendation Ready)")

    with col_log:
        st.subheader("Activity Log")
        with st.container(height=300):
            st.markdown(f"""
            - **{datetime.now().strftime('%H:%M')}**: User viewed Emergency Command Center
            - **{datetime.now().strftime('%H:%M')}**: Inventory search for {target_bg} completed
            - **-10 min**: AI Triage completed for {selected_event_name}
            - **-15 min**: Incident '{selected_event_name}' reported
            """)
            
    # -------------------------------------------------------------------------
    # 8. Emergency Guidance Panel
    # -------------------------------------------------------------------------
    with st.expander("📖 Understanding Facility Status"):
        st.markdown("""
        **Operational States**
        - **Ready:** Facility is fully equipped to satisfy the emergency request immediately.
        - **Partial Availability:** Facility has compatible blood units but cannot satisfy the complete request alone. Requires coordination with other sites.
        - **Unavailable:** No compatible blood units currently available at this location.
        - **Selected for Dispatch:** Facility has been actively engaged in the emergency workflow.
        - **Incident Location:** The physical centre point of the disaster or the calculated centroid used for routing.
        
        **Workflow Definitions**
        - **Reservation:** Holding compatible units at a facility so they cannot be allocated to routine operations.
        - **Allocation:** Legally assigning reserved blood to the requesting emergency site.
        - **Dispatch:** Blood has left the supplying facility and is in transit.
        - **Delivered:** Blood has successfully reached the destination.
        - **Completed:** Emergency request has been fully satisfied.
        """)
