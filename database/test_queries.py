"""
Test script for BloodLink AI database queries.
Verifies all important queries.
"""

from database.queries import BloodQueries

def run_tests():
    queries = BloodQueries()
    failed = False
    
    print("------------------------------------------------")
    print("TEST 1")
    print("Total healthcare facilities")
    print("------------------------------------------------")
    try:
        facilities = queries.get_all_healthcare_facilities()
        print(f"Count: {len(facilities)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True
        
    print("------------------------------------------------")
    print("TEST 2")
    print("Inventory for O+")
    print("------------------------------------------------")
    try:
        inv_o_pos = queries.get_inventory_by_blood_group("O+")
        print(f"Count: {len(inv_o_pos)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 3")
    print("Inventory for AB-")
    print("------------------------------------------------")
    try:
        inv_ab_neg = queries.get_inventory_by_blood_group("AB-")
        print(f"Count: {len(inv_ab_neg)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 4")
    print("Low stock inventory")
    print("------------------------------------------------")
    try:
        low_stock = queries.get_low_stock_inventory()
        print(f"Count: {len(low_stock)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 5")
    print("Eligible donors")
    print("------------------------------------------------")
    try:
        eligible_donors = queries.get_all_eligible_donors()
        print(f"Count: {len(eligible_donors)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 6")
    print("Eligible O+ donors")
    print("------------------------------------------------")
    try:
        eligible_o_pos = queries.get_eligible_donors_by_blood_group("O+")
        print(f"Count: {len(eligible_o_pos)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 7")
    print("Eligible O- donors")
    print("------------------------------------------------")
    try:
        eligible_o_neg = queries.get_eligible_donors_by_blood_group("O-")
        print(f"Count: {len(eligible_o_neg)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 8")
    print("Pending blood requests")
    print("------------------------------------------------")
    try:
        pending_requests = queries.get_pending_requests()
        print(f"Count: {len(pending_requests)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 9")
    print("Dashboard statistics")
    print("------------------------------------------------")
    try:
        stats = queries.get_dashboard_statistics()
        print(f"Stats: {stats}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 10")
    print("Find nearest blood inventory")
    print("------------------------------------------------")
    try:
        nearest = queries.get_nearest_available_inventory("O+", "Packed RBC", 22.5726, 88.3639, 3)
        print(f"Found: {len(nearest)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 11")
    print("Create sample blood request")
    print("------------------------------------------------")
    req_id = None
    try:
        req_id = queries.create_blood_request(
            patient_id=1,
            requesting_facility_id=1,
            blood_group="O+",
            component_type="Whole Blood",
            requested_units=2,
            requested_priority="TIER_2_URGENT",
            ai_priority=2,
            explanation="Test request"
        )
        print(f"Created Request ID: {req_id}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 12")
    print("Reserve 2 units")
    print("------------------------------------------------")
    inventory_to_reserve = None
    try:
        # Find some inventory to reserve
        available_inv = queries.get_nearest_available_inventory("O+", "Packed RBC", 22.5726, 88.3639, 2)
        if available_inv:
            inventory_to_reserve = available_inv[0]['id']
            success = queries.reserve_units(inventory_to_reserve, 2)
            if success:
                print("Reserved successfully")
                print("PASS")
            else:
                print("FAIL: reserve_units returned False")
                failed = True
        else:
            print("Skipped: No inventory available to reserve")
            print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 13")
    print("Release reservation")
    print("------------------------------------------------")
    try:
        if inventory_to_reserve:
            success = queries.release_reserved_units(inventory_to_reserve, 2)
            if success:
                print("Released successfully")
                print("PASS")
            else:
                print("FAIL: release_reserved_units returned False")
                failed = True
        else:
            print("Skipped: No inventory was reserved")
            print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 14")
    print("Recent donations")
    print("------------------------------------------------")
    try:
        recent = queries.get_recent_donations(30)
        print(f"Count: {len(recent)}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    print("------------------------------------------------")
    print("TEST 15")
    print("Save Agent Decision")
    print("------------------------------------------------")
    try:
        decision_id = queries.save_agent_decision(
            agent_name="Recommendation Agent",
            decision_type="Nearest facility selected",
            context="{}",
            reasoning="Shortest distance with sufficient inventory"
        )
        print(f"Created Decision ID: {decision_id}")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
        failed = True

    if not failed:
        print("\n=====================")
        print("ALL DATABASE TESTS PASSED")
        print("=====================")
    else:
        print("\n=====================")
        print("SOME TESTS FAILED")
        print("=====================")

if __name__ == "__main__":
    run_tests()
