"""
MCP Tools for Donor Management.
Provides structured, typed tools for donor search and WHO-compliant eligibility checking.
"""

from typing import Dict, Any, List
from datetime import datetime
from mcp_server.registry import registry
from database.queries import BloodQueries
from database.database import DatabaseManager
from utils.logger import logger

queries = BloodQueries()

@registry.register()
def find_eligible_donors(blood_group: str) -> Dict[str, Any]:
    """Find eligible donors for a specific blood group."""
    logger.info(f"Tool called: find_eligible_donors({blood_group})")
    try:
        donors = queries.get_eligible_donors_by_blood_group(blood_group)
        return {"status": "success", "data": donors}
    except Exception as e:
        logger.error(f"find_eligible_donors error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@registry.register()
def get_donor(donor_id: int) -> Dict[str, Any]:
    """Get donor details by ID."""
    logger.info(f"Tool called: get_donor({donor_id})")
    try:
        donor = queries.get_donor(donor_id)
        if donor:
            return {"status": "success", "data": donor}
        return {"status": "error", "message": "Donor not found."}
    except Exception as e:
        logger.error(f"get_donor error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@registry.register()
def search_nearby_donors(blood_group: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """Search for nearby eligible donors based on location."""
    logger.info(f"Tool called: search_nearby_donors({blood_group}, {latitude}, {longitude})")
    try:
        db = DatabaseManager()
        query = """
            SELECT *, 
                   ((latitude - ?) * (latitude - ?) + (longitude - ?) * (longitude - ?)) as distance_sq
            FROM Donor
            WHERE blood_group = ? 
              AND availability_status = 'Available'
              AND (eligible_after IS NULL OR eligible_after <= date('now'))
            ORDER BY distance_sq ASC
            LIMIT 50
        """
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (latitude, latitude, longitude, longitude, blood_group))
            results = [dict(row) for row in cursor.fetchall()]
            
        return {"status": "success", "data": results}
    except Exception as e:
        logger.error(f"search_nearby_donors error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@registry.register()
def check_donor_eligibility(donor_id: int) -> Dict[str, Any]:
    """
    Check if a donor is eligible based on WHO guidelines.
    Returns status: 'Eligible', 'Temporary Deferral', or 'Permanent Deferral'
    and detailed explanations.
    """
    logger.info(f"Tool called: check_donor_eligibility({donor_id})")
    try:
        donor = queries.get_donor(donor_id)
        if not donor:
            return {"status": "error", "message": "Donor not found."}

        issues = []
        is_permanent_deferral = False

        # 1. Age (WHO: 18 to 65 typically)
        age = donor.get('age', 0)
        if age < 18:
            issues.append(f"Age {age} is below minimum of 18.")
        elif age > 65:
            issues.append(f"Age {age} is above maximum of 65.")
            is_permanent_deferral = True

        # 2. Weight (WHO: >= 45.0 kg)
        weight = donor.get('weight', 0.0)
        if weight < 45.0:
            issues.append(f"Weight {weight}kg is below minimum of 45.0kg.")

        # 3. Hemoglobin (WHO: >= 12.0 for female, >= 13.0 for male)
        hb = donor.get('hemoglobin')
        gender = donor.get('gender', 'Unknown').lower()
        if hb is not None:
            if gender == 'female' and hb < 12.0:
                issues.append(f"Hemoglobin {hb}g/dL is below female minimum of 12.0g/dL.")
            elif gender == 'male' and hb < 13.0:
                issues.append(f"Hemoglobin {hb}g/dL is below male minimum of 13.0g/dL.")
            elif gender not in ['male', 'female'] and hb < 12.5: # Generic fallback
                issues.append(f"Hemoglobin {hb}g/dL is below minimum threshold.")
        else:
            issues.append("Hemoglobin level not recorded; screening required.")

        # 4. Blood Pressure (WHO: Sys 100-140, Dia 60-90)
        bp = donor.get('blood_pressure')
        if bp:
            try:
                sys_str, dia_str = bp.split('/')
                sys, dia = int(sys_str), int(dia_str)
                if not (100 <= sys <= 140):
                    issues.append(f"Systolic BP {sys} is out of normal range (100-140).")
                if not (60 <= dia <= 90):
                    issues.append(f"Diastolic BP {dia} is out of normal range (60-90).")
            except Exception:
                issues.append(f"Invalid blood pressure format: {bp}.")
        else:
            issues.append("Blood pressure not recorded; screening required.")

        # 5. Medical Clearance
        if not donor.get('medical_clearance', True):
            issues.append("Donor lacks medical clearance.")
            is_permanent_deferral = True

        # 6. Availability Status
        status = donor.get('availability_status')
        if status == 'Permanently Deferred':
            issues.append("Donor is already marked as Permanently Deferred.")
            is_permanent_deferral = True
        elif status == 'Temporarily Deferred':
            issues.append("Donor is currently under a Temporary Deferral.")

        # 7. Last Donation Date / Frequency (WHO: 56 days whole blood)
        eligible_after = donor.get('eligible_after')
        if eligible_after:
            try:
                eligible_date = datetime.strptime(eligible_after, "%Y-%m-%d").date()
                if eligible_date > datetime.now().date():
                    issues.append(f"Donor is deferred until {eligible_after}.")
            except ValueError:
                pass
                
        last_donation = donor.get('last_donation_date')
        if last_donation:
            try:
                last_don = datetime.strptime(last_donation, "%Y-%m-%d").date()
                days_since = (datetime.now().date() - last_don).days
                if days_since < 56:
                    issues.append(f"Only {days_since} days since last donation (minimum 56 days).")
            except ValueError:
                pass

        # Determine Final Eligibility Status
        if is_permanent_deferral:
            final_status = "Permanent Deferral"
            explanation = "Donor is permanently deferred. Reasons: " + "; ".join(issues)
        elif issues:
            final_status = "Temporary Deferral"
            explanation = "Donor is temporarily deferred. Reasons: " + "; ".join(issues)
        else:
            final_status = "Eligible"
            explanation = "Donor meets all WHO eligibility criteria."

        return {
            "status": "success", 
            "data": {
                "eligibility_status": final_status,
                "explanation": explanation,
                "issues": issues
            }
        }
    except Exception as e:
        logger.error(f"check_donor_eligibility error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
