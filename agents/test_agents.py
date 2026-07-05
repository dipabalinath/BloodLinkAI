"""
Test script for BloodLink AI Agents.
Tests end-to-end execution of agents via the Orchestrator and individual testing.
"""

from agents.agent_factory import get_agents
from agents.orchestrator import BloodLinkOrchestrator
from utils.logger import logger

def run_tests():
    print("--- Starting BloodLink AI Agents Test ---")
    
    # Instantiate all agents
    agents = get_agents()
    orchestrator = BloodLinkOrchestrator()
    all_passed = True

    print("\n--- Testing Individual Agents ---")
    
    # 1. Eligibility Agent
    eligibility_agent = agents.get("eligibility")
    try:
        # Eligible
        req1 = "Check if this 30 year old donor with 14 hemoglobin and 120/80 BP is eligible."
        res1 = eligibility_agent.execute(
            user_request=req1, 
            manual_params={"age": 30, "weight": 70, "hemoglobin": 14.0, "blood_pressure": "120/80"}
        )
        if res1.get("eligibility") == "Eligible":
            print("[PASS] Eligibility Agent: Eligible donor")
        else:
            print(f"[FAIL] Eligibility Agent: Expected Eligible, got {res1.get('eligibility')}")
            all_passed = False

        # Ineligible
        req2 = "Check if this 16 year old donor is eligible."
        res2 = eligibility_agent.execute(
            user_request=req2, 
            manual_params={"age": 16, "weight": 70, "hemoglobin": 14.0, "blood_pressure": "120/80"}
        )
        if "Deferral" in str(res2.get("eligibility")):
            print("[PASS] Eligibility Agent: Ineligible donor")
        else:
            print(f"[FAIL] Eligibility Agent: Expected Deferral, got {res2.get('eligibility')}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Eligibility Agent threw an exception: {e}")
        all_passed = False

    # 2. Priority Agent
    priority_agent = agents.get("priority")
    try:
        # Thalassemia request
        res3 = priority_agent.execute("Determine priority for a routine thalassemia patient.", patient_condition="routine thalassemia")
        if "TIER_3" in str(res3.get("priority")):
            print("[PASS] Priority Agent: Thalassemia request maps to TIER_3")
        else:
            print(f"[FAIL] Priority Agent: Thalassemia expected TIER_3, got {res3.get('priority')}")
            all_passed = False

        # Birthing mother emergency
        res4 = priority_agent.execute("Determine priority for birthing mother with active hemorrhage.", patient_condition="birthing mother active hemorrhage")
        if "TIER_1" in str(res4.get("priority")):
            print("[PASS] Priority Agent: Birthing mother maps to TIER_1")
        else:
            print(f"[FAIL] Priority Agent: Birthing mother expected TIER_1, got {res4.get('priority')}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Priority Agent threw an exception: {e}")
        all_passed = False

    # 3. Inventory & Recommendation Agent (Search)
    inventory_agent = agents.get("inventory")
    try:
        # Inventory search / Compatible blood search
        res5 = inventory_agent.execute(
            "Find O- blood nearby.", 
            blood_group="O-", 
            latitude=37.77, 
            longitude=-122.41, 
            required_units=2
        )
        if "Success" in str(res5.get("status")) or "No Inventory" in str(res5.get("status")):
            print("[PASS] Inventory Agent: Executed inventory and compatible search")
        else:
            print(f"[FAIL] Inventory Agent: Expected Success, got {res5.get('status')}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Inventory Agent threw an exception: {e}")
        all_passed = False

    # 4. Notification Agent
    notification_agent = agents.get("notification")
    try:
        # Generate Notifications
        res6 = notification_agent.execute(
            "Notify donors for urgent O+ need.",
            blood_group="O+",
            urgency="immediate",
            location="General Hospital",
            inventory_available=False
        )
        if "Success" in str(res6.get("status")) or "No Donors Found" in str(res6.get("status")):
            print("[PASS] Notification Agent: Generated notifications successfully")
        else:
            print(f"[FAIL] Notification Agent: Unexpected status {res6.get('status')}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Notification Agent threw an exception: {e}")
        all_passed = False

    print("\n--- Testing Orchestrator (Supervisor) ---")
    try:
        res7 = orchestrator.process_request(
            "We have a birthing mother in shock needing O- blood immediately at Central Hospital.",
            context_params={
                "blood_group": "O-",
                "patient_condition": "birthing mother in shock",
                "urgency": "immediate",
                "location": "Central Hospital",
                "latitude": 37.77,
                "longitude": -122.41,
                "inventory_available": False
            }
        )
        if res7.get("status") == "Success" and len(res7.get("agents_involved", [])) > 0:
            print("[PASS] Orchestrator: Successfully parsed, delegated, and merged response")
        else:
            print(f"[FAIL] Orchestrator: Expected Success, got {res7.get('status')}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Orchestrator threw an exception: {e}")
        all_passed = False

    print("\n-----------------------------------------")
    if all_passed:
        print("OVERALL RESULT: ALL TESTS PASSED.")
    else:
        print("OVERALL RESULT: SOME TESTS FAILED.")

if __name__ == "__main__":
    run_tests()
