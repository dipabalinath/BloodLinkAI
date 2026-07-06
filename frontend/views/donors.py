import streamlit as st
import pandas as pd
from datetime import date, datetime
from utils.logger import logger
from frontend.utils.database import fetch_data, search_donors, get_donor_history
from frontend.utils.geocoder import geocode_address
from frontend.utils.donor_workflow import update_donor_status, record_donation_and_recovery

def render_donors():
    """Render the full BBIS Donor Management Workflow."""
    st.header("🩸 Donor Management")
    st.write("Manage donor lifecycle from registration and clinical assessment to donation and recovery.")

    db = st.session_state.get('db_manager')
    orchestrator = st.session_state.get('orchestrator')
    if not db or not orchestrator:
        st.error("System components not initialized.")
        return
        
    # Display any pending notifications from a previous run
    if 'donor_notification' in st.session_state and st.session_state.donor_notification:
        notif = st.session_state.donor_notification
        if notif.startswith("⚠") or notif.startswith("❌"):
            st.warning(notif)
        elif notif.startswith("✅") or "success" in notif.lower():
            st.success(notif)
        else:
            st.info(notif)
        st.session_state.donor_notification = None
        
    eligibility_agent = orchestrator.agents.get('eligibility')

    sections = [
        "📊 Dashboard", 
        "📝 Register Donor", 
        "🩺 Clinical Assessment", 
        "✅ Eligible Pool", 
        "📜 Donation History"
    ]
    
    st.radio("Navigation", sections, horizontal=True, label_visibility="collapsed", key="donor_active_section")
    st.markdown("---")
    
    active_section = st.session_state.donor_active_section
    
    # Log the restored section for debugging/tracing
    if active_section:
        logger.info(f"Restoring section: {active_section.split(' ', 1)[-1]}")

    # Section 1: Dashboard
    if active_section == "📊 Dashboard":
        st.subheader("Operational Overview")
        
        counts = fetch_data("SELECT availability_status, COUNT(*) as cnt FROM Donor GROUP BY availability_status")
        status_map = {row['availability_status']: row['cnt'] for _, row in counts.iterrows()} if not counts.empty else {}
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Registered Donors", sum(status_map.values()))
        c2.metric("Awaiting Assessment", status_map.get('Awaiting Clinical Assessment', 0))
        c3.metric("Eligible Donors", status_map.get('Eligible', 0))
        c4.metric("Available for Donation", status_map.get('Available for Donation', 0))
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Recovery Period", status_map.get('Recovery Period', 0))
        c6.metric("Temporarily Deferred", status_map.get('Temporarily Deferred', 0))
        c7.metric("Permanently Deferred", status_map.get('Permanently Deferred', 0))
        
        today_donations = fetch_data("SELECT COUNT(*) as cnt FROM DonationHistory WHERE date(donation_date) = date('now')")
        month_donations = fetch_data("SELECT COUNT(*) as cnt FROM DonationHistory WHERE strftime('%Y-%m', donation_date) = strftime('%Y-%m', 'now')")
        c8.metric("Donations Today", today_donations.iloc[0]['cnt'] if not today_donations.empty else 0)
        
        st.markdown("---")
        df_all = search_donors()
        if not df_all.empty:
            st.dataframe(df_all, use_container_width=True, hide_index=True)

    # Section 2: Register Donor
    elif active_section == "📝 Register Donor":
        st.subheader("Register New Donor")
        st.info("Register demographic information. Clinical assessment is performed in the next workflow step.")
        
        with st.form("register_donor_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                f_name = st.text_input("First Name (required)")
                l_name = st.text_input("Last Name (required)")
                gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
                mobile = st.text_input("Mobile Number")
                email = st.text_input("Email")
            with col2:
                bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
                address = st.text_input("Address (optional)")
                city = st.text_input("City (required)")
                state = st.text_input("State (required)")
                pin_code = st.text_input("PIN Code (required)")
                
            med_notes = st.text_area("Medical Notes (optional)")
            st.caption("Location coordinates are generated automatically in the background.")
                
            submitted = st.form_submit_button("Register Donor", type="primary")
            if submitted:
                if f_name and l_name and city and state and pin_code:
                    age = (date.today() - dob).days // 365
                    if age < 18:
                        st.error("Donor must be at least 18 years old.")
                    else:
                        with st.spinner("Geocoding & Saving..."):
                            lat, lng = geocode_address(address, city, state, pin_code)
                            if lat is None or lng is None:
                                lat, lng = 0.0, 0.0
                                
                            try:
                                with db.connect() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT INTO Donor (first_name, last_name, age, weight, gender, blood_group, phone, email, address, city, state, pin_code, medical_notes, latitude, longitude, availability_status)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Awaiting Clinical Assessment')
                                    """, (f_name, l_name, age, 60.0, gender, bg, mobile, email, address, city, state, pin_code, med_notes, lat, lng))
                                    conn.commit()
                                st.session_state.donor_notification = "✅ Donor successfully registered and is awaiting clinical assessment."
                                logger.info("Donor registered successfully.")
                                logger.info("Refreshing donor dashboard...")
                                fetch_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Database error: {e}")
                else:
                    st.warning("Please fill in all required fields (First Name, Last Name, City, State, PIN Code).")

    # Section 3: Clinical Assessment
    elif active_section == "🩺 Clinical Assessment":
        st.subheader("Clinical Assessment & AI Decision Support")
        
        with st.expander("🩺 Eligibility Criteria Guide"):
            st.markdown("""
**Basic Requirements**
• Age: 18 - 65 years
• Weight: > 45 kg (varies by component)
• Haemoglobin: > 12.5 g/dL

**Common Deferrals (Temporary)**
• Pregnancy/Breastfeeding (defer 6-12 months)
• Recent Surgery (defer 6 months)
• Recent Tattoo/Piercing (defer 6 months)
• Recent Vaccination (defer 2-4 weeks)
• Infection/Fever (defer until resolved)

**Common Deferrals (Permanent)**
• Chronic Diseases (e.g., severe cardiac, renal, liver disease)
• HIV/Hepatitis/Syphilis positive
• Insulin-dependent Diabetes
            """)
        
        awaiting_df = fetch_data("SELECT id as `Donor ID`, first_name || ' ' || last_name as Name, blood_group as `Blood Group`, gender as Gender, age as Age, city as City, created_at as `Registration Date`, availability_status as `Current Status` FROM Donor WHERE availability_status = 'Awaiting Clinical Assessment'")
        
        if awaiting_df.empty:
            st.info("No donors currently awaiting assessment.")
        else:
            st.write("### Awaiting Clinical Assessment")
            st.dataframe(awaiting_df, use_container_width=True, hide_index=True)
            
            request_ids = awaiting_df['Donor ID'].tolist()
            default_idx = 0
            if st.session_state.get('clinical_selected_id') in request_ids:
                default_idx = request_ids.index(st.session_state['clinical_selected_id'])
            
            selected_id = st.selectbox("Select Donor to Assess", request_ids, index=default_idx)
            st.session_state['clinical_selected_id'] = selected_id
            
            if selected_id:
                donor = fetch_data("SELECT * FROM Donor WHERE id = ?", (selected_id,)).iloc[0]
                st.markdown("---")
                st.write(f"### Assessing: {donor['first_name']} {donor['last_name']} ({donor['blood_group']})")
                
                with st.form(f"clinical_assessment_form_{selected_id}"):
                    st.write("**General Information**")
                    c1, c2, c3 = st.columns(3)
                    assessed_age = c1.number_input("Age", value=int(donor['age']))
                    assessed_gender = c2.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(donor['gender']) if donor['gender'] in ["Male", "Female", "Other"] else 0)
                    weight = c3.number_input("Weight (kg)", value=float(donor['weight']) if donor['weight'] else 60.0, step=0.1)
                    
                    st.write("**Vital Signs**")
                    c4, c5, c6, c7 = st.columns(4)
                    hb = c4.number_input("Haemoglobin (g/dL)", value=13.0, step=0.1)
                    sys_bp = c5.number_input("Systolic BP", value=120)
                    dia_bp = c6.number_input("Diastolic BP", value=80)
                    pulse = c7.number_input("Pulse", value=75)
                    
                    st.write("**Donation History & Medical History**")
                    c8, c9 = st.columns(2)
                    last_don = c8.date_input("Last Donation Date", value=None)
                    prev_count = c9.number_input("Previous Donation Count", value=int(donor['total_donations']))
                    
                    st.write("**Medical Flags**")
                    m1, m2, m3 = st.columns(3)
                    preg = m1.checkbox("Pregnancy Status (if applicable)")
                    meds = m1.checkbox("Current Medication")
                    surg = m1.checkbox("Recent Surgery")
                    tat = m2.checkbox("Recent Tattoo/Piercing")
                    vax = m2.checkbox("Recent Vaccination")
                    inf = m2.checkbox("Recent Infection")
                    chron = m3.checkbox("Chronic Disease")
                    trvl = m3.checkbox("Travel History")
                    alc = m3.checkbox("Alcohol Consumption")
                    
                    notes = st.text_area("Clinical Notes")
                    
                    eval_btn = st.form_submit_button("🩺 Evaluate Eligibility", type="primary")
                    
                if eval_btn:
                    logger.info("Running AI eligibility assessment...")
                    with st.spinner("AI analyzing clinical data..."):
                        params = {
                            "Age": assessed_age,
                            "Gender": assessed_gender,
                            "Weight": weight,
                            "Haemoglobin": hb,
                            "Systolic": sys_bp,
                            "Diastolic": dia_bp,
                            "Pulse": pulse,
                            "Last Donation Date": str(last_don) if last_don else None,
                            "Pregnant/Breastfeeding": preg,
                            "Current Medication": meds,
                            "Recent Surgery": surg,
                            "Recent Tattoo/Piercing (<6 months)": tat,
                            "Recent Vaccination": vax,
                            "Any Infectious Disease": inf,
                            "Chronic Disease": chron,
                            "Travel History": trvl,
                            "Alcohol Consumption": alc,
                            "Notes": notes
                        }
                        
                        try:
                            # Update weight in db just in case
                            with db.connect() as conn:
                                conn.cursor().execute("UPDATE Donor SET weight = ? WHERE id = ?", (weight, selected_id))
                                conn.commit()
                                
                            res = eligibility_agent.execute(
                                user_request="Perform clinical eligibility assessment", 
                                manual_params=params
                            )
                            
                            st.session_state[f'ai_res_{selected_id}'] = res
                        except Exception as e:
                            st.error(f"Agent error: {e}")
                
                # If evaluation exists in state
                ai_res = st.session_state.get(f'ai_res_{selected_id}')
                if ai_res and ai_res.get("status") != "error":
                    st.success("AI Assessment Complete")
                    with st.container(border=True):
                        st.markdown(f"### AI Recommendation: **{ai_res.get('eligibility')}**")
                        st.markdown(f"**Clinical Reasoning:** {ai_res.get('reasoning')}")
                        st.markdown("**Risk Factors Identified:**")
                        for k,v in ai_res.get('risk_indicators', {}).items():
                            if v == "❌": st.markdown(f"- {k}")
                        st.markdown("**Recommended Action:**")
                        for rec in ai_res.get('recommendations', []):
                            st.markdown(f"- {rec}")
                            
                        c_app, c_over = st.columns(2)
                        with c_app:
                            if st.button("✅ Approve Recommendation", type="primary", use_container_width=True):
                                update_donor_status(selected_id, ai_res.get('eligibility'), ai_res.get('reasoning'), ai_res.get('eligibility'), "Clinician")
                                st.session_state.donor_notification = f"✅ Status updated to {ai_res.get('eligibility')}!"
                                logger.info("Eligibility approved.")
                                logger.info(f"Eligibility updated for donor {selected_id}")
                                logger.info("Refreshing eligible donor pool...")
                                logger.info("Refreshing donor statistics...")
                                logger.info("Refreshing donor dashboard...")
                                fetch_data.clear()
                                st.rerun()
                                
                        with c_over:
                            override_stat = st.selectbox("Override Status", ["Eligible", "Temporarily Deferred", "Permanently Deferred"], label_visibility="collapsed")
                            if st.button("⚠️ Override Recommendation", use_container_width=True, type="secondary"):
                                update_donor_status(selected_id, override_stat, ai_res.get('reasoning'), override_stat, "Clinician")
                                st.session_state.donor_notification = f"✅ Status overridden to {override_stat}!"
                                logger.info(f"Eligibility updated for donor {selected_id}")
                                logger.info("Refreshing donor dashboard...")
                                fetch_data.clear()
                                st.rerun()

    # Section 4: Eligible Donor Pool & Donation
    elif active_section == "✅ Eligible Pool":
        st.subheader("Eligible Donor Pool")
        elig_df = fetch_data("SELECT id as `Donor ID`, first_name || ' ' || last_name as Name, blood_group as `Blood Group`, city as City, last_donation_date as `Last Donation`, assessment_date as `Assessment Date`, total_donations as `Donation Count`, availability_status as `Current Status` FROM Donor WHERE availability_status IN ('Eligible', 'Available for Donation')")
        
        if elig_df.empty:
            st.info("No eligible donors ready for donation.")
        else:
            st.dataframe(elig_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.write("### Record Donation")
            with st.form("record_donation_form"):
                elig_ids = elig_df['Donor ID'].tolist()
                default_elig_idx = 0
                if st.session_state.get('record_donor_id') in elig_ids:
                    default_elig_idx = elig_ids.index(st.session_state['record_donor_id'])
                
                ed_id = st.selectbox("Select Donor ID", elig_ids, index=default_elig_idx)
                st.session_state['record_donor_id'] = ed_id
                
                f_df = fetch_data("SELECT id, name FROM HealthcareFacility")
                f_map = {row['name']: row['id'] for _, row in f_df.iterrows()} if not f_df.empty else {"Main Center": 1}
                center = st.selectbox("Donation Centre", list(f_map.keys()))
                comp = st.selectbox("Blood Component", ["Whole Blood", "Platelets", "Plasma", "Packed RBC"])
                units = st.number_input("Units Collected", min_value=1, value=1)
                vol = st.number_input("Volume (mL)", min_value=100, value=450)
                
                if st.form_submit_button("Record Donation", type="primary"):
                    succ, days, next_date = record_donation_and_recovery(ed_id, f_map[center], comp, vol)
                    if succ:
                        st.session_state.donor_notification = f"✅ Donation recorded successfully! Donor moved to Recovery Period for {days} days. Eligible again on {next_date}."
                        logger.info(f"Donation recorded for donor {ed_id}")
                        logger.info("Refreshing donor dashboard...")
                        fetch_data.clear()
                        st.rerun()
                    else:
                        st.error("Failed to record donation.")

    # Section 5: Donation History
    elif active_section == "📜 Donation History":
        st.subheader("Donation History")
        h_df = fetch_data("""
            SELECT dh.donation_date as `Donation Date`, d.first_name || ' ' || d.last_name as Donor, d.blood_group as `Blood Group`, 
                   dh.blood_component as Component, dh.volume_ml as `Volume (mL)`, hf.name as `Donation Centre`, dh.status as Status 
            FROM DonationHistory dh 
            JOIN Donor d ON dh.donor_id = d.id 
            JOIN HealthcareFacility hf ON dh.facility_id = hf.id 
            ORDER BY dh.donation_date DESC
        """)
        if not h_df.empty:
            # Simple filters
            c1, c2 = st.columns(2)
            bg_filt = c1.selectbox("Filter by Blood Group", ["All"] + list(h_df['Blood Group'].unique()))
            if bg_filt != "All":
                h_df = h_df[h_df['Blood Group'] == bg_filt]
            st.dataframe(h_df, use_container_width=True, hide_index=True)
        else:
            st.info("No donations recorded yet.")
