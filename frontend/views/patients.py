import streamlit as st
import pandas as pd
import plotly.express as px
from utils.logger import logger
from frontend.utils.database import (
    get_patient_dashboard_metrics,
    get_patients_by_blood_group,
    get_patients_by_hospital,
    search_patients
)

def render_patients():
    """Render the Patients Management page."""
    st.header("🛏️ Patients Management")
    st.write("Manage patient profiles, monitor clinical priorities, and generate AI blood recommendations.")

    db = st.session_state.get('db_manager')
    orchestrator = st.session_state.get('orchestrator')
    
    if not db or not orchestrator:
        st.error("System components not initialized.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Patients List", "🔍 Patient Details", "➕ Add/Edit Patient"])
    
    # ---------------- Dashboard ----------------
    with tab1:
        st.subheader("Patients Overview")
        metrics = get_patient_dashboard_metrics()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Patients", metrics.get("total_patients", 0))
        col2.metric("Critical Patients (High Priority)", metrics.get("critical_patients", 0))
        col3.metric("Pending Blood Requests", metrics.get("pending_requests", 0))
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            bg_df = get_patients_by_blood_group()
            if not bg_df.empty:
                fig1 = px.pie(bg_df, names='blood_group', values='count', title="Patients by Blood Group")
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No blood group data available.")
                
        with c2:
            hosp_df = get_patients_by_hospital()
            if not hosp_df.empty:
                fig2 = px.bar(hosp_df, x='hospital', y='count', title="Patients by Hospital", color='hospital')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No hospital data available.")
                
        st.markdown("---")
        st.subheader("Active Blood Requests")
        
        from frontend.utils.database import get_all_requests
        dash_req_df = get_all_requests()
        if not dash_req_df.empty:
            st.dataframe(dash_req_df, use_container_width=True, hide_index=True)
        else:
            st.info("No active blood requests in the system.")

    # ---------------- Patients List ----------------
    with tab2:
        st.subheader("Patient Database")
        
        with st.expander("Clinical Priority Guide"):
            st.markdown("""
**🔴 Critical (Immediate)**
Life-threatening emergencies requiring immediate blood transfusion.
Examples:
• Massive haemorrhage
• Trauma
• Obstetric haemorrhage
• Shock

**🟠 High (Urgent)**
Blood required within a few hours.
Examples:
• Emergency surgery
• Active bleeding
• Severe anaemia

**🟡 Medium (Priority)**
Blood needed but patient is currently stable.
Examples:
• Scheduled surgery
• Oncology
• Chronic transfusion

**🟢 Low (Routine)**
Routine requests that can safely wait.
Examples:
• Elective procedures
• Non-urgent transfusions
            """)
        
        from frontend.utils.database import get_all_requests
        
        c_search, c_bg, c_hosp = st.columns([2, 1, 1])
        with c_search:
            search_query = st.text_input("Search by Name, Blood Group or Hospital")
        with c_bg:
            bg_filter = st.selectbox("Filter Blood Group", ["All", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        with c_hosp:
            with db.connect() as conn:
                facs_df = pd.read_sql("SELECT name FROM HealthcareFacility", conn)
                fac_list = facs_df['name'].tolist() if not facs_df.empty else []
            hosp_filter = st.selectbox("Filter Hospital", ["All"] + fac_list)
            
        df = get_all_requests()
        if not df.empty:
            # Drop unnecessary columns to match the requested streamlined view
            if 'Treating Physician' in df.columns:
                df = df.drop(columns=['Treating Physician'])
            
            # Rename Current Request Status to Request Status
            if 'Current Request Status' in df.columns:
                df = df.rename(columns={'Current Request Status': 'Request Status'})
                
            # Filter
            if search_query:
                df = df[df.apply(lambda row: search_query.lower() in str(row.values).lower(), axis=1)]
                
            if bg_filter != "All":
                df = df[df['Blood Group'] == bg_filter]
            if hosp_filter != "All":
                df = df[df['Hospital'] == hosp_filter]
                
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No active blood requests found for patients.")

    # ---------------- Patient Details & AI Recommendation ----------------
    with tab3:
        st.subheader("Patient Details & AI Recommendation")
        
        full_df = search_patients()
        
        if full_df.empty:
            st.warning("No patients available in the database.")
        else:
            # Create a selector formatted as "ID - Name"
            patient_options = full_df.apply(lambda row: f"{row['ID']} - {row['First']} {row['Last']}", axis=1).tolist()
            selected_str = st.selectbox("Select Patient", patient_options)
            selected_id = int(selected_str.split(" - ")[0])
            
            patient_row = full_df[full_df['ID'] == selected_id].iloc[0]
            
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.write(f"**Name:** {patient_row['First']} {patient_row['Last']}")
                st.write(f"**Blood Group:** {patient_row['Type']}")
                st.write(f"**Hospital:** {patient_row['Hospital']}")
            with col_det2:
                st.write(f"**Medical Condition:** {patient_row.get('Condition', 'None')}")
                
                patient_priority = patient_row.get('Priority', '⚪ Not Yet Assessed')
                if patient_priority == "⚪ Not Yet Assessed":
                    # Attempt to fetch from latest blood request
                    with db.connect() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT requested_priority FROM BloodRequest WHERE patient_id = ? ORDER BY request_date DESC LIMIT 1", (selected_id,))
                        row = cursor.fetchone()
                        if row and row[0]:
                            raw_prio = row[0]
                            mapping = {
                                "TIER_1_IMMEDIATE": "🔴 Critical (Immediate)",
                                "TIER_2_URGENT": "🟠 High (Urgent)",
                                "TIER_3_SCHEDULED": "🟡 Medium (Scheduled)",
                                "TIER_3_PRIORITY": "🟡 Medium (Scheduled)",
                                "TIER_4_ELECTIVE": "🟢 Low (Elective)"
                            }
                            patient_priority = mapping.get(raw_prio, raw_prio)
                
                st.write(f"**Clinical Priority:** {patient_priority}")
                
            st.markdown("---")
            st.write("### Clinical Actions")
            
            c_act1, c_act2, c_act3 = st.columns(3)
            
            if 'show_blood_request' not in st.session_state:
                st.session_state.show_blood_request = False
            
            with c_act1:
                if st.button("🩸 Request Blood", use_container_width=True, type="primary"):
                    st.session_state.show_blood_request = True
            with c_act2:
                if st.button("🤖 Generate AI Recommendation", use_container_width=True, type="primary"):
                    st.session_state.run_ai_assessment = True
            with c_act3:
                if st.button("📄 View History", use_container_width=True, type="secondary"):
                    st.info("Patient history feature coming soon.")

            # ---------------- REQUEST BLOOD DIALOG ----------------
            if st.session_state.get('show_blood_request'):
                st.markdown("---")
                st.subheader(f"Request Blood for {patient_row['First']} {patient_row['Last']}")
                with st.form("blood_request_form"):
                    st.write(f"**Patient ID:** {selected_id} | **Hospital:** {patient_row['Hospital']} | **Blood Group:** {patient_row['Type']}")
                    
                    req_comp = st.selectbox("Blood Component", ["Whole Blood", "Packed RBC", "Fresh Frozen Plasma", "Platelets", "Cryoprecipitate"])
                    req_units = st.number_input("Required Units", min_value=1, max_value=20, value=1)
                    req_indication = st.text_input("Clinical Indication", placeholder="e.g., Active bleeding, Scheduled surgery")
                    req_date = st.date_input("Required By Date")
                    req_priority_display = st.selectbox("Clinical Priority *", ["🔴 Critical (Immediate)", "🟠 High (Urgent)", "🟡 Medium (Scheduled)", "🟢 Low (Elective)"])
                    req_emergency = st.checkbox("🚨 Emergency Flag")
                    req_notes = st.text_area("Additional Notes")
                    
                    submit_req = st.form_submit_button("Submit Blood Request", type="primary")
                    
                    if submit_req:
                        with st.spinner("Processing request..."):
                            try:
                                # Map back to canonical values
                                priority_db_map = {
                                    "🔴 Critical (Immediate)": "TIER_1_IMMEDIATE",
                                    "🟠 High (Urgent)": "TIER_2_URGENT",
                                    "🟡 Medium (Scheduled)": "TIER_3_SCHEDULED",
                                    "🟢 Low (Elective)": "TIER_4_ELECTIVE"
                                }
                                ai_priority = priority_db_map.get(req_priority_display, "TIER_3_SCHEDULED")
                                reason = "Clinically Assigned"
                                        
                                # Insert into DB
                                with db.connect() as conn:
                                    cursor = conn.cursor()
                                    # Get facility ID from patient
                                    cursor.execute("SELECT facility_id FROM Patient WHERE id = ?", (selected_id,))
                                    fac_id = cursor.fetchone()[0]
                                    
                                    cursor.execute("""
                                        INSERT INTO BloodRequest (patient_id, requesting_facility_id, blood_group, component_type, requested_units, requested_priority, explanation, status)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (selected_id, fac_id, patient_row['Type'], req_comp, req_units, ai_priority, reason, 'Pending'))
                                    new_req_id = cursor.lastrowid
                                    conn.commit()
                                
                                # Run Inventory Matcher
                                from agents.inventory_agent import InventoryAgent
                                ia = InventoryAgent()
                                
                                # Get lat/lng for facility
                                with db.connect() as conn:
                                    cursor.execute("SELECT latitude, longitude FROM HealthcareFacility WHERE id = ?", (fac_id,))
                                    loc = cursor.fetchone()
                                    lat, lng = (loc[0], loc[1]) if loc else (0.0, 0.0)
                                    
                                inv_res = ia.execute(
                                    user_request=f"Find {req_units} units of {patient_row['Type']} {req_comp}.",
                                    blood_group=patient_row['Type'],
                                    component_type=req_comp,
                                    latitude=lat,
                                    longitude=lng,
                                    required_units=req_units
                                )
                                
                                # Save to session state to display confirmation card outside the form
                                st.session_state.last_blood_request = {
                                    'id': new_req_id,
                                    'priority': ai_priority,
                                    'reason': reason,
                                    'inventory_matches': inv_res.get("recommended_facilities", []),
                                    'inventory_summary': inv_res.get("summary", ""),
                                    'comp': req_comp,
                                    'units': req_units
                                }
                                st.session_state.show_blood_request = False
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Failed to create request: {e}")
                                
            # ---------------- POST-SUBMISSION CONFIRMATION ----------------
            if 'last_blood_request' in st.session_state:
                lbr = st.session_state.last_blood_request
                st.success("✅ Blood Request Created Successfully")
                st.info(f"**Request ID:** {lbr['id']} | **Priority:** {lbr['priority']} | **Component:** {lbr['units']} units of {lbr['comp']}\n\n**AI Reasoning:** {lbr['reason']}")
                
                st.write("### AI Inventory Availability")
                if lbr['inventory_matches']:
                    st.dataframe(pd.DataFrame(lbr['inventory_matches']), use_container_width=True)
                else:
                    st.warning("No compatible stock found nearby.")
                    
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    st.button("Reserve Blood", use_container_width=True, type="primary")
                with col_btn2:
                    st.button("Notify Eligible Donors", use_container_width=True)
                with col_btn3:
                    if st.button("Clear Confirmation", use_container_width=True):
                        del st.session_state.last_blood_request
                        st.rerun()
            
            # ---------------- BLOOD REQUEST HISTORY ----------------
            st.markdown("---")
            st.write("### Blood Request History")
            
            with db.connect() as conn:
                pt_reqs_df = pd.read_sql("""
                    SELECT br.id as `Request ID`, br.request_date as `Date`, br.component_type as `Blood Component`, 
                           br.requested_units as `Units Requested`, br.requested_priority as `Priority`, 
                           br.status as `Status`, br.allocated_units as `Fulfilled Units`, h.name as `Facility`
                    FROM BloodRequest br
                    JOIN HealthcareFacility h ON br.requesting_facility_id = h.id
                    WHERE br.patient_id = ? 
                    ORDER BY br.request_date DESC
                """, conn, params=(selected_id,))
                
            if not pt_reqs_df.empty:
                from frontend.utils.database import format_priorities
                pt_reqs_df = format_priorities(pt_reqs_df, "Priority")
                st.dataframe(pt_reqs_df, use_container_width=True, hide_index=True)
            else:
                st.info("No active blood requests for this patient.")

            if st.session_state.get('run_ai_assessment'):
                st.markdown("---")
                
                # Fetch active request
                active_req = None
                with db.connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, component_type, requested_units, requested_priority, status 
                        FROM BloodRequest 
                        WHERE patient_id = ? AND status IN ('Pending', 'Partially Fulfilled') 
                        ORDER BY request_date DESC LIMIT 1
                    """, (selected_id,))
                    row = cursor.fetchone()
                    if row:
                        active_req = {
                            'id': row[0],
                            'component': row[1],
                            'units': row[2],
                            'priority': row[3],
                            'status': row[4]
                        }
                
                if not active_req:
                    st.info("No active blood request exists for this patient.\n\nPlease create a Blood Request before requesting an AI clinical assessment.")
                    if st.button("Create Blood Request", key="btn_create_blood_req"):
                        st.session_state.show_blood_request = True
                        st.session_state.run_ai_assessment = False
                        st.rerun()
                else:
                    st.write("### 🩸 BloodLink AI Clinical Decision Support")
                    with st.spinner("⏳ BloodLink AI is analysing the patient's information..."):
                        try:
                            # Pass context to orchestrator
                            prompt = (
                                f"Patient {patient_row['First']} {patient_row['Last']} (ID: {selected_id}) at {patient_row['Hospital']}. "
                                f"Blood group: {patient_row['Type']}. "
                                f"Clinical Indication / Condition: {patient_row.get('Condition', 'Unknown')}. "
                                f"Active Blood Request ID: {active_req['id']}. "
                                f"Component: {active_req['component']}, Units: {active_req['units']}. "
                                f"Assigned Priority: {active_req['priority']}, Status: {active_req['status']}. "
                                "Please provide a clinical summary based on this blood request."
                            )
                            context_params = {
                                "patient_condition": patient_row.get('Condition', 'Unknown'),
                                "blood_group": patient_row['Type'],
                                "component_type": active_req['component'],
                                "required_units": active_req['units'],
                                "requested_priority": active_req['priority'],
                                "assigned_priority": patient_priority,
                                "location": patient_row['Hospital'],
                                "facility": patient_row['Hospital'],
                                "request_id": active_req['id']
                            }
                            res = orchestrator.process_request(prompt, context_params=context_params)
                            if res.get('status') == 'Success':
                                logger.info("Rendering Patient Clinical Summary")
                                logger.info(res)
                                
                                c_sum = res.get('clinical_summary')
                                
                                if c_sum and isinstance(c_sum, dict):
                                    with st.container(border=True):
                                        st.subheader("📋 Clinical Summary")
                                        st.markdown(c_sum.get('summary', 'Not available'))
                                        
                                        st.subheader("⚖️ Priority Assessment")
                                        prio = c_sum.get('priority', {})
                                        if prio:
                                            st.markdown(f"**{prio.get('label', '')}**\n\n{prio.get('reason', '')}")
                                        else:
                                            st.markdown('Not available')
                                        
                                        st.subheader("🩸 Blood Availability")
                                        inv = c_sum.get('inventory', {})
                                        if inv:
                                            st.markdown(f"**{inv.get('available_units', 0)} units of {inv.get('blood_group', '')} {inv.get('component', '')}**\n\n{inv.get('explanation', '')}")
                                        else:
                                            st.markdown('Not available')
                                            
                                        st.subheader("🏥 Recommended Facility")
                                        fac = c_sum.get('facility', {})
                                        if fac:
                                            st.markdown(f"**{fac.get('name', '')}**\n\n{fac.get('address', '')}\n\nDistance: {fac.get('distance_km', 0.0)} km\n\n{fac.get('reason', '')}")
                                        else:
                                            st.markdown('Not available')
                                            
                                        st.subheader("💡 Recommended Clinical Actions")
                                        st.markdown(c_sum.get('recommendation', 'Not available'))
                                        
                                        st.subheader("👥 Donor Notification Recommendation")
                                        st.markdown(c_sum.get('donor_notification', 'Not available'))
                                        
                                        st.subheader("⚠️ Clinical Risks")
                                        st.markdown(c_sum.get('clinical_risks', 'Not available'))
                                        
                                        st.success(f"**🎯 Overall Recommendation:**\n\n{c_sum.get('overall', 'Not available')}")
                                
                                elif res.get('final_answer'):
                                    st.markdown(res.get('final_answer'))
                                else:
                                    st.warning("No clinical summary was generated by the AI.")
                            else:
                                logger.error(f"Orchestrator Error: {res.get('error')}")
                                st.error("Unable to generate an AI recommendation at this time.")
                        except Exception as e:
                            logger.error(f"AI Exception: {e}", exc_info=True)
                            st.error("Unable to generate an AI recommendation at this time.")
                    
                    if st.button("Close Clinical Summary", key="close_ai"):
                        st.session_state.run_ai_assessment = False
                        st.rerun()

            st.markdown("---")
            st.write("### Danger Zone")
            if st.button("Delete Patient", type="secondary"):
                try:
                    with db.connect() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM Patient WHERE id = ?", (selected_id,))
                        conn.commit()
                    st.success(f"Patient {selected_id} deleted successfully. Please refresh.")
                except Exception as e:
                    st.error(f"Error deleting patient: {e}")

    # ---------------- Add/Edit Patient ----------------
    with tab4:
        st.subheader("Add or Edit Patient")
        st.info("To edit a patient, enter their existing Patient ID. Leave blank to register a new patient.")
        with st.form("patient_form"):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                p_id = st.text_input("Patient ID (leave blank for new)")
                f_name = st.text_input("First Name")
                l_name = st.text_input("Last Name")
                bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
            with col_f2:
                with db.connect() as conn:
                    fac_df = pd.read_sql("SELECT id, name FROM HealthcareFacility", conn)
                fac_dict = dict(zip(fac_df.name, fac_df.id))
                
                if fac_dict:
                    hosp = st.selectbox("Facility", list(fac_dict.keys()))
                else:
                    hosp = None
                    st.error("No facilities found.")
                    
                cond = st.text_input("Medical Condition")
                priority = st.number_input("Priority Score (1-10)", min_value=1, max_value=10, value=5)
                
            sub = st.form_submit_button("Save Patient Profile", type="primary")
            
            if sub:
                if not f_name or not l_name or not hosp:
                    st.warning("First Name, Last Name, and Facility are required.")
                else:
                    try:
                        with db.connect() as conn:
                            cursor = conn.cursor()
                            fac_id = fac_dict[hosp]
                            if p_id:
                                cursor.execute("""
                                    UPDATE Patient 
                                    SET first_name=?, last_name=?, blood_group=?, facility_id=?, medical_condition=?, priority_score=? 
                                    WHERE id=?
                                """, (f_name, l_name, bg, fac_id, cond, priority, p_id))
                                st.success(f"Patient {p_id} updated successfully!")
                            else:
                                cursor.execute("""
                                    INSERT INTO Patient (first_name, last_name, blood_group, facility_id, medical_condition, priority_score) 
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (f_name, l_name, bg, fac_id, cond, priority))
                                st.success("New patient registered successfully!")
                            conn.commit()
                    except Exception as e:
                        st.error(f"Database error: {e}")
