"""
Eligibility Skill for BloodLink AI.
Evaluates blood donor eligibility against WHO guidelines.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from skills.shared_models import EligibilityResult
from database.queries import BloodQueries
from utils.logger import logger

class EligibilitySkill:
    def __init__(self):
        self.queries = BloodQueries()

    def evaluate_donor(self, donor_id: int) -> EligibilityResult:
        """
        Evaluate a donor's eligibility using their database record.
        """
        logger.info(f"Evaluating eligibility for donor ID: {donor_id}")
        try:
            donor = self.queries.get_donor(donor_id)
            if not donor:
                return EligibilityResult(
                    status="Error",
                    reason="Donor not found in database.",
                    metadata={"donor_id": donor_id}
                )
            
            # Pass dictionary values to manual evaluation
            return self.evaluate_manual(
                age=donor.get('age'),
                weight=donor.get('weight'),
                hemoglobin=donor.get('hemoglobin'),
                blood_pressure=donor.get('blood_pressure'),
                last_donation_date=donor.get('last_donation_date'),
                medical_clearance=donor.get('medical_clearance', True),
                has_infectious_disease=False, # Assuming false if cleared in basic schema
                availability_status=donor.get('availability_status')
            )
        except Exception as e:
            logger.error(f"Error evaluating donor {donor_id}: {e}")
            return EligibilityResult(
                status="Error",
                reason=f"Internal evaluation error: {str(e)}",
                metadata={"donor_id": donor_id}
            )

    def evaluate_manual(
        self, 
        age: Optional[int] = None, 
        weight: Optional[float] = None, 
        hemoglobin: Optional[float] = None, 
        blood_pressure: Optional[str] = None, 
        last_donation_date: Optional[str] = None,
        medical_clearance: bool = True,
        has_infectious_disease: bool = False,
        availability_status: Optional[str] = None
    ) -> EligibilityResult:
        """
        Evaluate eligibility manually using provided parameters.
        """
        issues = []
        is_permanent_deferral = False

        # 1. Infectious Disease
        if has_infectious_disease:
            issues.append("Donor has a serious infectious disease.")
            is_permanent_deferral = True

        # 2. Medical Clearance
        if not medical_clearance:
            issues.append("Donor lacks medical clearance.")
            is_permanent_deferral = True

        # 3. Availability Status
        if availability_status == 'Permanently Deferred':
            issues.append("Donor is already marked as Permanently Deferred.")
            is_permanent_deferral = True
        elif availability_status == 'Temporarily Deferred':
            issues.append("Donor is currently under a Temporary Deferral.")

        # 4. Age (18-65)
        if age is not None:
            if age < 18:
                issues.append(f"Age {age} is below minimum of 18.")
            elif age > 65:
                issues.append(f"Age {age} is above maximum of 65.")
                is_permanent_deferral = True
        else:
            issues.append("Age not recorded.")

        # 5. Weight (>= 45 kg)
        if weight is not None:
            if weight < 45.0:
                issues.append(f"Weight {weight}kg is below minimum of 45.0kg.")
        else:
            issues.append("Weight not recorded.")

        # 6. Hemoglobin (>= 12.5 g/dL)
        if hemoglobin is not None:
            if hemoglobin < 12.5:
                issues.append(f"Hemoglobin {hemoglobin}g/dL is below minimum of 12.5g/dL.")
        else:
            issues.append("Hemoglobin not recorded.")

        # 7. Blood Pressure (Normal is roughly 100-140 / 60-90)
        if blood_pressure:
            try:
                sys_str, dia_str = blood_pressure.split('/')
                sys, dia = int(sys_str), int(dia_str)
                if not (100 <= sys <= 140) or not (60 <= dia <= 90):
                    issues.append(f"Blood pressure {blood_pressure} is outside normal ranges (100-140/60-90).")
            except Exception:
                issues.append(f"Invalid blood pressure format: {blood_pressure}")
        else:
            issues.append("Blood pressure not recorded.")

        # 8. Last Donation Date (>= 90 days)
        if last_donation_date:
            try:
                last_don = datetime.strptime(last_donation_date, "%Y-%m-%d").date()
                days_since = (datetime.now().date() - last_don).days
                if days_since < 90:
                    issues.append(f"Only {days_since} days since last donation (minimum 90 days required).")
            except ValueError:
                issues.append(f"Invalid date format for last donation: {last_donation_date}")

        # Final Decision
        metadata = {
            "age": age,
            "weight": weight,
            "hemoglobin": hemoglobin,
            "issues": issues
        }

        if is_permanent_deferral:
            return EligibilityResult(
                status="Permanent Deferral",
                reason="Donor is permanently deferred. Reasons: " + "; ".join(issues),
                metadata=metadata
            )
        elif issues:
            return EligibilityResult(
                status="Temporary Deferral",
                reason="Donor is temporarily deferred. Reasons: " + "; ".join(issues),
                metadata=metadata
            )
        else:
            return EligibilityResult(
                status="Eligible",
                reason="Donor meets all WHO eligibility criteria.",
                metadata=metadata
            )
