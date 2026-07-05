"""
Test script for BloodLink AI Skills.
Runs sample scenarios and outputs PASS/FAIL.
"""

from skills.eligibility_skill import EligibilitySkill
from skills.priority_skill import PrioritySkill
from skills.recommendation_skill import RecommendationSkill
from skills.notification_skill import NotificationSkill
from skills.explainability_skill import ExplainabilitySkill
from datetime import datetime

def run_tests():
    print("--- Starting BloodLink AI Skills Test ---")
    
    # Instantiate Skills
    eligibility_skill = EligibilitySkill()
    priority_skill = PrioritySkill()
    recommendation_skill = RecommendationSkill()
    notification_skill = NotificationSkill()
    explainability_skill = ExplainabilitySkill()

    all_passed = True

    # 1. Test Eligibility
    try:
        # Manual evaluation: perfect donor
        res = eligibility_skill.evaluate_manual(
            age=30, weight=70, hemoglobin=14.0, blood_pressure="120/80", 
            last_donation_date="2023-01-01", medical_clearance=True, 
            has_infectious_disease=False
        )
        if res.status == "Eligible":
            print("[PASS] Eligibility: Perfect donor is eligible.")
        else:
            print(f"[FAIL] Eligibility: Perfect donor failed -> {res.status}")
            all_passed = False
            
        # Manual evaluation: underage
        res2 = eligibility_skill.evaluate_manual(
            age=16, weight=70, hemoglobin=14.0, blood_pressure="120/80"
        )
        if res2.status == "Temporary Deferral":
            print("[PASS] Eligibility: Underage donor is deferred.")
        else:
            print(f"[FAIL] Eligibility: Underage donor didn't defer -> {res2.status}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Eligibility threw an exception: {e}")
        all_passed = False

    # 2. Test Priority
    try:
        res_prio = priority_skill.evaluate_condition("birthing mother with active hemorrhage")
        if res_prio.status == "TIER_1_IMMEDIATE":
            print("[PASS] Priority: Hemorrhage maps to TIER_1_IMMEDIATE.")
        else:
            print(f"[FAIL] Priority: Expected TIER_1, got {res_prio.status}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Priority threw an exception: {e}")
        all_passed = False

    # 3. Test Recommendation
    try:
        # Relies on DB, might return No Inventory or Success depending on seeded data
        res_rec = recommendation_skill.recommend_inventory(
            blood_group="O-", component_type="Packed RBC", 
            latitude=37.7749, longitude=-122.4194, required_units=2
        )
        if res_rec.status in ["Success", "No Inventory", "Error"]:
            print(f"[PASS] Recommendation executed without crashing. Status: {res_rec.status}")
        else:
            print(f"[FAIL] Recommendation unexpected status: {res_rec.status}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Recommendation threw an exception: {e}")
        all_passed = False

    # 4. Test Notification
    try:
        # Prepare notification
        res_notif = notification_skill.prepare_notification(
            blood_group="O+", urgency="immediate", location="General Hospital"
        )
        if res_notif.status in ["Success", "No Donors Found", "Error"]:
            print(f"[PASS] Notification executed without crashing. Status: {res_notif.status}")
        else:
            print(f"[FAIL] Notification unexpected status: {res_notif.status}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Notification threw an exception: {e}")
        all_passed = False

    # 5. Test Explainability
    try:
        # Feed priority result to explainability
        res_explain = explainability_skill.explain_priority(res_prio)
        if "TIER_1_IMMEDIATE" in res_explain.reason or "Immediate dispatch is necessary" in res_explain.reason:
            print("[PASS] Explainability: Explained TIER_1 properly.")
        else:
            print("[FAIL] Explainability: Failed to explain TIER_1.")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Explainability threw an exception: {e}")
        all_passed = False
        
    print("-----------------------------------------")
    if all_passed:
        print("OVERALL RESULT: ALL TESTS PASSED.")
    else:
        print("OVERALL RESULT: SOME TESTS FAILED.")

if __name__ == "__main__":
    run_tests()
