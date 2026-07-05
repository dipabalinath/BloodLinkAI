"""
Test script for verifying MCP tools.
"""

from mcp_server.registry import registry
import json

# Ensure all tools are registered by importing the modules
import mcp_server.tools.inventory_tools
import mcp_server.tools.donor_tools
import mcp_server.tools.request_tools
import mcp_server.tools.notification_tools
import mcp_server.tools.analytics_tools

def print_result(title: str, result: dict):
    print(f"\n{'='*50}")
    print(title)
    print(f"{'='*50}")
    # Pretty print the dictionary, truncating large lists for readability
    if 'data' in result and isinstance(result['data'], list) and len(result['data']) > 3:
        print(f"Status: {result.get('status')}")
        print(f"Items found: {len(result['data'])}")
        print("First 3 items:")
        print(json.dumps(result['data'][:3], indent=2, default=str))
        print("...")
    else:
        print(json.dumps(result, indent=2, default=str))

def run_tests():
    print(f"Total Registered Tools: {len(registry.list_tools())}")

    # 1. Inventory Search
    find_inventory = registry.get_tool("find_inventory")
    print_result(
        "TEST: Inventory Search (O+, Packed RBC, Min 2 units)", 
        find_inventory(blood_group="O+", component_type="Packed RBC", minimum_units=2)
    )

    # 2. Eligible Donor Search
    find_eligible_donors = registry.get_tool("find_eligible_donors")
    print_result(
        "TEST: Eligible Donor Search (O+)", 
        find_eligible_donors(blood_group="O+")
    )

    # 3. Pending Requests
    get_pending_requests = registry.get_tool("get_pending_requests")
    print_result(
        "TEST: Pending Requests", 
        get_pending_requests()
    )

    # 4. Low Stock
    get_low_stock = registry.get_tool("get_low_stock")
    print_result(
        "TEST: Low Stock Facilities", 
        get_low_stock()
    )

    # 5. Dashboard
    dashboard = registry.get_tool("dashboard")
    print_result(
        "TEST: Dashboard Statistics", 
        dashboard()
    )

if __name__ == "__main__":
    run_tests()
