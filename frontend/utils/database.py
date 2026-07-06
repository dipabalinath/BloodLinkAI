import streamlit as st
import pandas as pd
import json
from typing import Optional, Dict, Any, List
from utils.logger import logger

@st.cache_data(ttl=30)
def fetch_data(query: str, params: tuple = ()) -> pd.DataFrame:
    """
    Execute a read-only SQL query and return a cached Pandas DataFrame.
    Automatically handles database connections and exceptions.
    
    Args:
        query (str): The SQL SELECT query.
        params (tuple): Query parameters for safe parameterized execution.
        
    Returns:
        pd.DataFrame: The resulting dataset, or an empty DataFrame on error.
    """
    db = st.session_state.get('db_manager')
    if not db:
        logger.error("fetch_data called but db_manager not in session_state.")
        return pd.DataFrame()
        
    try:
        with db.connect() as conn:
            df = pd.read_sql(query, conn, params=params)
            return df
    except Exception as e:
        logger.error(f"Database query failed: {query} | Error: {e}")
        st.error(f"Database query failed. Please check logs.")
        return pd.DataFrame()

# ---------------- Dashboard Metrics ----------------

def get_dashboard_metrics() -> Optional[Dict[str, Any]]:
    """Fetch high-level metrics for the dashboard using shared db_manager."""
    try:
        fac = fetch_data("SELECT COUNT(*) as count FROM HealthcareFacility")
        don = fetch_data("SELECT COUNT(*) as count FROM Donor")
        pat = fetch_data("SELECT COUNT(*) as count FROM Patient")
        inv = fetch_data("SELECT COALESCE(SUM(units_available),0) as count FROM BloodInventory")
        res = fetch_data("SELECT COALESCE(SUM(reserved_units), 0) as count FROM BloodInventory")
        req = fetch_data("SELECT COUNT(*) as count FROM BloodRequest WHERE status IN ('Pending','Partially Fulfilled')")
        emg = fetch_data("SELECT COUNT(*) as count FROM BloodRequest WHERE requested_priority='TIER_1_IMMEDIATE' AND status IN ('Pending','Partially Fulfilled')")
        
        metrics = {
            "facilities": int(fac.iloc[0]['count']) if not fac.empty else 0,
            "donors": int(don.iloc[0]['count']) if not don.empty else 0,
            "patients": int(pat.iloc[0]['count']) if not pat.empty else 0,
            "blood_units": int(inv.iloc[0]['count']) if not inv.empty else 0,
            "reserved_units": int(res.iloc[0]['count']) if not res.empty else 0,
            "active_requests": int(req.iloc[0]['count']) if not req.empty else 0,
            "emergency_requests": int(emg.iloc[0]['count']) if not emg.empty else 0
        }
        
        logger.info(
            f"Dashboard metrics loaded:\n"
            f"Facilities: {metrics['facilities']}\n"
            f"Donors: {metrics['donors']}\n"
            f"Patients: {metrics['patients']}\n"
            f"Available Blood Units: {metrics['blood_units']}\n"
            f"Reserved Blood Units: {metrics['reserved_units']}\n"
            f"Active Requests: {metrics['active_requests']}\n"
            f"Emergency Requests: {metrics['emergency_requests']}"
        )
        return metrics
    except Exception as e:
        logger.error(f"Failed to load dashboard metrics: {e}")
        return None

def get_patient_dashboard_metrics() -> Dict[str, Any]:
    metrics = {
        "total_patients": 0,
        "critical_patients": 0,
        "pending_requests": 0
    }
    
    total_df = fetch_data("SELECT COUNT(*) as cnt FROM Patient")
    crit_df = fetch_data("SELECT COUNT(*) as cnt FROM Patient WHERE ai_priority = 1 OR priority_score >= 8")
    req_df = fetch_data("SELECT COUNT(*) as cnt FROM BloodRequest WHERE status = 'Pending'")
    
    if not total_df.empty: metrics['total_patients'] = total_df.iloc[0]['cnt']
    if not crit_df.empty: metrics['critical_patients'] = crit_df.iloc[0]['cnt']
    if not req_df.empty: metrics['pending_requests'] = req_df.iloc[0]['cnt']
    
    return metrics

# ---------------- Charts Data ----------------

def get_inventory_by_group() -> pd.DataFrame:
    return fetch_data("SELECT blood_group, SUM(units_available) as total_units FROM BloodInventory GROUP BY blood_group")

def get_patients_by_blood_group() -> pd.DataFrame:
    return fetch_data("SELECT blood_group, COUNT(id) as count FROM Patient GROUP BY blood_group")

def get_patients_by_hospital() -> pd.DataFrame:
    return fetch_data("SELECT h.name as hospital, COUNT(p.id) as count FROM Patient p JOIN HealthcareFacility h ON p.facility_id = h.id GROUP BY h.name")

def get_donor_group_distribution() -> pd.DataFrame:
    return fetch_data("SELECT blood_group, COUNT(id) as count FROM Donor GROUP BY blood_group")

def get_donors_by_city() -> pd.DataFrame:
    return fetch_data("SELECT city, COUNT(id) as count FROM Donor GROUP BY city")

def get_monthly_donations() -> pd.DataFrame:
    return fetch_data("SELECT strftime('%Y-%m', donation_date) as month, SUM(volume_ml) as total_vol FROM DonationHistory GROUP BY month ORDER BY month")

def get_requests_by_status() -> pd.DataFrame:
    return fetch_data("SELECT status, COUNT(id) as count FROM BloodRequest GROUP BY status")

def get_emergency_trends() -> pd.DataFrame:
    return fetch_data("SELECT strftime('%Y-%m', declared_at) as month, severity_level, COUNT(id) as count FROM EmergencyEvent GROUP BY month, severity_level")

def get_ai_decisions() -> pd.DataFrame:
    return fetch_data("SELECT agent_name, COUNT(id) as count FROM AgentDecisionLog GROUP BY agent_name")

def get_expiring_aggregate(days: int = 14) -> pd.DataFrame:
    query = f"SELECT expiry_date, SUM(units_available) as units FROM BloodInventory WHERE units_available > 0 AND expiry_date <= date('now', '+{days} days') GROUP BY expiry_date"
    return fetch_data(query)

# ---------------- Tables Data ----------------

def get_low_inventory_alerts(limit: int = 5) -> pd.DataFrame:
    query = """
        SELECT h.name as facility, b.blood_group, b.units_available, b.minimum_threshold 
        FROM BloodInventory b
        JOIN HealthcareFacility h ON b.facility_id = h.id
        WHERE b.units_available <= b.minimum_threshold
        ORDER BY b.units_available ASC
        LIMIT ?
    """
    return fetch_data(query, (limit,))

def get_recent_activities(limit: int = 5) -> pd.DataFrame:
    query = """
        SELECT id as Request_ID, blood_group as Blood_Group, requested_units as Units, status as Status, request_date as Date
        FROM BloodRequest
        ORDER BY request_date DESC
        LIMIT ?
    """
    return fetch_data(query, (limit,))

def get_expiring_inventory(days: int = 7) -> pd.DataFrame:
    query = f"""
        SELECT 
            h.name as Facility, h.address as Address, h.city as City, 
            b.blood_group as `Blood Group`, b.component_type as Component, 
            b.units_available as `Available Units`, b.collection_date as `Collection Date`, 
            b.expiry_date as `Expiry Date`
        FROM BloodInventory b
        JOIN HealthcareFacility h ON b.facility_id = h.id
        WHERE b.expiry_date <= date('now', '+{days} days') AND b.units_available > 0 
        ORDER BY b.expiry_date ASC
    """
    return fetch_data(query)

def get_active_emergencies() -> pd.DataFrame:
    query = 'SELECT id AS "Event ID", event_name AS "Event", location_city AS "City", severity_level AS "Severity", expected_units AS "Required Units", latitude AS "latitude", longitude AS "longitude", declared_at AS "Declared At", status AS "Status" FROM EmergencyEvent WHERE is_active = 1'
    return fetch_data(query)

def get_recent_notifications(limit: int = 10) -> pd.DataFrame:
    return fetch_data("SELECT notification_type as Type, message as Message, recipient_type as Recipient, delivery_channel as Channel, sent_at as Time FROM Notification WHERE notification_type = 'EMERGENCY' OR notification_type = 'URGENT' ORDER BY sent_at DESC LIMIT ?", (limit,))

def get_active_reservations() -> pd.DataFrame:
    query = """
        SELECT
            r.reservation_date AS "Reservation Date",
            h.name AS "Hospital",
            h.address AS "Hospital Address",
            br.id AS "Blood Request ID",
            b.blood_group AS "Blood Group",
            b.component_type AS "Component",
            r.reserved_units AS "Reserved Units",
            r.status AS "Status",
            r.expires_at AS "Reserved Until",
            COALESCE(r.reserved_by_agent, 'System') AS "Reserved By Agent"
        FROM Reservation r
        JOIN BloodInventory b
            ON r.inventory_id = b.id
        JOIN HealthcareFacility h
            ON b.facility_id = h.id
        LEFT JOIN BloodRequest br
            ON r.request_id = br.id
        ORDER BY r.reservation_date DESC
    """
    return fetch_data(query)

def get_donor_history(donor_id: int) -> pd.DataFrame:
    return fetch_data("SELECT donation_date as Date, volume_ml as Volume, blood_component as Component, status as Status, remarks as Remarks FROM DonationHistory WHERE donor_id = ? ORDER BY donation_date DESC", (donor_id,))

def get_all_requests(limit: int = 50) -> pd.DataFrame:
    query = """
        SELECT 
            br.id AS `Request ID`,
            p.first_name || ' ' || p.last_name AS `Patient Name`,
            'N/A' AS Age,
            'N/A' AS Gender,
            br.blood_group AS `Blood Group`,
            br.component_type AS `Component Requested`,
            br.requested_units AS `Units Requested`,
            br.requested_priority AS Priority,
            h.name AS Hospital,
            'N/A' AS `Treating Physician`,
            br.status AS `Current Request Status`,
            br.request_date AS `Date Requested`
        FROM BloodRequest br
        JOIN Patient p ON br.patient_id = p.id
        JOIN HealthcareFacility h ON br.requesting_facility_id = h.id
        ORDER BY br.request_date DESC
        LIMIT ?
    """
    df = fetch_data(query, (limit,))
    return format_priorities(df, "Priority")

def get_facility_locations(blood_group: str = None) -> pd.DataFrame:
    query = "SELECT h.name, h.facility_type, CAST(h.latitude AS REAL) as lat, CAST(h.longitude AS REAL) as lon FROM HealthcareFacility h"
    if blood_group and blood_group != "All":
        query += " JOIN BloodInventory b ON h.id = b.facility_id WHERE b.blood_group = ? AND b.units_available > 0 AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL AND h.latitude != 0 AND h.longitude != 0 GROUP BY h.id"
        return fetch_data(query, (blood_group,))
    else:
        query += " WHERE h.latitude IS NOT NULL AND h.longitude IS NOT NULL AND h.latitude != 0 AND h.longitude != 0"
        return fetch_data(query)

def get_donor_locations() -> pd.DataFrame:
    return fetch_data("SELECT latitude as lat, longitude as lon, blood_group FROM Donor WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND latitude != 0 AND longitude != 0")

# ---------------- Search / Filtering ----------------

def search_donors(search_query: str = "") -> pd.DataFrame:
    query = """
        SELECT 
            id as "Donor ID", 
            first_name || ' ' || last_name as "Name", 
            blood_group as "Blood Group", 
            gender as "Gender", 
            city as "City", 
            state as "State",
            pin_code as "PIN Code",
            phone as "Mobile",
            last_donation_date as "Last Donation", 
            availability_status as "Eligibility Status" 
        FROM Donor
    """
    if search_query:
        query += " WHERE first_name LIKE ? OR last_name LIKE ? OR blood_group LIKE ? OR city LIKE ?"
        like_q = f"%{search_query}%"
        return fetch_data(query, (like_q, like_q, like_q, like_q))
    return fetch_data(query)

def format_priorities(df: pd.DataFrame, col_name: str = "Priority") -> pd.DataFrame:
    if col_name in df.columns:
        mapping = {
            1: "🔴 Critical (Immediate)",
            2: "🟠 High (Urgent)",
            3: "🟡 Medium (Scheduled)",
            4: "🟢 Low (Elective)",
            "1": "🔴 Critical (Immediate)",
            "2": "🟠 High (Urgent)",
            "3": "🟡 Medium (Scheduled)",
            "4": "🟢 Low (Elective)",
            "TIER_1_IMMEDIATE": "🔴 Critical (Immediate)",
            "TIER_2_URGENT": "🟠 High (Urgent)",
            "TIER_3_SCHEDULED": "🟡 Medium (Scheduled)",
            "TIER_4_ELECTIVE": "🟢 Low (Elective)",
            "TIER_3_PRIORITY": "🟡 Medium (Scheduled)"
        }
        
        # Apply mapping
        df[col_name] = df[col_name].map(mapping).fillna(df[col_name])
        
        # Replace empty, None, or unmapped NaN with "Not Yet Assessed"
        df[col_name] = df[col_name].fillna("⚪ Not Yet Assessed")
        df[col_name] = df[col_name].replace("None", "⚪ Not Yet Assessed")
        df[col_name] = df[col_name].replace("", "⚪ Not Yet Assessed")
        
        categories = [
            "🔴 Critical (Immediate)",
            "🟠 High (Urgent)",
            "🟡 Medium (Scheduled)",
            "🟢 Low (Elective)",
            "⚪ Not Yet Assessed"
        ]
        
        # We need to make sure all values are within the categories, otherwise they become NaN.
        # So we force anything not in categories to "⚪ Not Yet Assessed"
        df[col_name] = df[col_name].apply(lambda x: x if x in categories else "⚪ Not Yet Assessed")
        
        df[col_name] = pd.Categorical(df[col_name], categories=categories, ordered=True)
    return df

def search_patients(search_query: str = "") -> pd.DataFrame:
    query = """
        SELECT p.id as ID, p.first_name as First, p.last_name as Last, p.blood_group as Type, 
               p.medical_condition as Condition, p.priority_score as Priority, 
               p.ai_priority as AI_Tier, p.priority_reason as AI_Reason,
               h.name as Hospital
        FROM Patient p
        JOIN HealthcareFacility h ON p.facility_id = h.id
    """
    if search_query:
        query += " WHERE p.first_name LIKE ? OR p.last_name LIKE ? OR p.blood_group LIKE ? OR h.name LIKE ?"
        like_q = f"%{search_query}%"
        df = fetch_data(query, (like_q, like_q, like_q, like_q))
    else:
        df = fetch_data(query)
    return format_priorities(df, "Priority")

# ---------------- Dashboard & Operations ----------------

def get_blood_requests_metrics() -> Dict[str, Any]:
    query_pending = "SELECT COUNT(*) as count FROM BloodRequest WHERE status = 'Pending'"
    query_urgent = "SELECT COUNT(*) as count FROM BloodRequest WHERE status = 'Pending' AND requested_priority IN ('1', '2', 'TIER_1_IMMEDIATE', 'TIER_2_URGENT')"
    query_reserved = "SELECT SUM(reserved_units) as count FROM Reservation WHERE status = 'Active'"
    query_fulfilled = "SELECT COUNT(*) as count FROM BloodRequest WHERE status = 'Fulfilled' AND date(request_date) = date('now')"
    query_cancelled = "SELECT COUNT(*) as count FROM BloodRequest WHERE status = 'Cancelled'"
    
    pending = fetch_data(query_pending).iloc[0]['count'] if not fetch_data(query_pending).empty else 0
    urgent = fetch_data(query_urgent).iloc[0]['count'] if not fetch_data(query_urgent).empty else 0
    
    reserved_df = fetch_data(query_reserved)
    reserved = reserved_df.iloc[0]['count'] if not reserved_df.empty and pd.notna(reserved_df.iloc[0]['count']) else 0
    
    fulfilled = fetch_data(query_fulfilled).iloc[0]['count'] if not fetch_data(query_fulfilled).empty else 0
    cancelled = fetch_data(query_cancelled).iloc[0]['count'] if not fetch_data(query_cancelled).empty else 0
    
    return {
        "Pending Requests": pending,
        "Urgent Requests": urgent,
        "Reserved Units": int(reserved),
        "Fulfilled Today": fulfilled,
        "Cancelled Requests": cancelled
    }

def execute_query(query: str, params: tuple = ()) -> None:
    db = st.session_state.get('db_manager')
    if not db:
        logger.error("execute_query called but db_manager not in session_state.")
        return
    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
    except Exception as e:
        logger.error(f"execute_query failed: {query} | Error: {e}")

def update_request_status(request_id: int, status: str):
    execute_query("UPDATE BloodRequest SET status = ? WHERE id = ?", (status, request_id))

def get_request_details(request_id: int) -> Dict[str, Any]:
    query = """
        SELECT 
            br.id as request_id,
            p.first_name || ' ' || p.last_name as patient_name,
            h.name as facility_name,
            h.latitude,
            h.longitude,
            br.blood_group,
            br.component_type,
            br.requested_units,
            br.requested_priority,
            br.status,
            br.explanation
        FROM BloodRequest br
        JOIN Patient p ON br.patient_id = p.id
        JOIN HealthcareFacility h ON br.requesting_facility_id = h.id
        WHERE br.id = ?
    """
    df = fetch_data(query, (request_id,))
    if df.empty:
        return {}
    return df.iloc[0].to_dict()
