from database.database import DatabaseManager
from datetime import datetime, timedelta
from utils.logger import logger

def update_donor_status(donor_id: int, new_status: str, ai_rec: str = None, final_dec: str = None, user: str = 'System'):
    db = DatabaseManager()
    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            if new_status in ['Eligible', 'Temporarily Deferred', 'Permanently Deferred']:
                cursor.execute("""
                    UPDATE Donor 
                    SET availability_status = ?, 
                        assessment_date = CURRENT_TIMESTAMP, 
                        assessed_by = ?, 
                        ai_recommendation = ?, 
                        final_clinical_decision = ?
                    WHERE id = ?
                """, (new_status, user, ai_rec, final_dec, donor_id))
            else:
                cursor.execute("UPDATE Donor SET availability_status = ? WHERE id = ?", (new_status, donor_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to update donor status: {e}")
        return False

def record_donation_and_recovery(donor_id: int, facility_id: int, component: str, volume_ml: int):
    db = DatabaseManager()
    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            
            # Record Donation
            cursor.execute("""
                INSERT INTO DonationHistory (donor_id, facility_id, donation_date, volume_ml, blood_component, status)
                VALUES (?, ?, date('now'), ?, ?, 'Testing')
            """, (donor_id, facility_id, volume_ml, component))
            
            # Calculate Recovery Period
            cursor.execute("SELECT gender FROM Donor WHERE id = ?", (donor_id,))
            donor = cursor.fetchone()
            gender = donor['gender'] if donor else 'Male'
            
            days = 56 # default
            if component == 'Whole Blood':
                days = 90 if gender == 'Female' else 56
            elif component == 'Platelets':
                days = 7
            elif component == 'Plasma':
                days = 28
                
            eligible_after = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Update Donor
            cursor.execute("""
                UPDATE Donor 
                SET availability_status = 'Recovery Period', 
                    last_donation_date = date('now'), 
                    total_donations = total_donations + 1,
                    eligible_after = ?
                WHERE id = ?
            """, (eligible_after, donor_id))
            
            conn.commit()
            return True, days, eligible_after
    except Exception as e:
        logger.error(f"Failed to record donation: {e}")
        return False, 0, None
