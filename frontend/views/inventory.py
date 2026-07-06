import streamlit as st
import pandas as pd
from utils.logger import logger

# Import registry which automatically discovers and registers MCP tools
from mcp_server.registry import registry
import mcp_server.tools.inventory_tools 
from frontend.utils.database import get_expiring_inventory, get_active_reservations

def render_inventory():
    """Render the Inventory Management page."""
    st.header("📦 Inventory Management")
    st.write("Manage blood units, monitor low stock, and handle reservations.")

    # Get MCP tools
    find_inventory = registry.get_tool("find_inventory")
    reserve_units = registry.get_tool("reserve_units")
    release_reservation = registry.get_tool("release_reservation")
    get_low_stock = registry.get_tool("get_low_stock")
    
    if not all([find_inventory, reserve_units, release_reservation, get_low_stock]):
        st.error("Some MCP inventory tools are missing. Ensure server is initialized.")
        return

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Search Inventory", "⚠️ Expiry & Low Stock", "🔄 Reservations"])

    # Tab 1: Search Inventory
    with tab1:
        st.subheader("Search Blood Units")
        
        with st.expander("ℹ️ Blood Components Guide"):
            st.markdown("""
**Whole Blood**
• Used for: Severe blood loss, trauma.
• Shelf Life: 35-42 days (refrigerated).

**Packed Red Blood Cells (RBC)**
• Used for: Anaemia, surgery, bleeding.
• Shelf Life: 42 days (refrigerated).

**Platelets**
• Used for: Cancer treatments, dengue, bleeding disorders.
• Shelf Life: 5-7 days (room temperature with agitation).

**Fresh Frozen Plasma (FFP)**
• Used for: Clotting factor deficiencies, liver disease.
• Shelf Life: Up to 1 year (frozen at -18°C).
            """)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            bg_filter = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        with col2:
            comp_filter = st.selectbox("Component", ["Packed RBC", "Plasma", "Platelets", "Whole Blood"])
        with col3:
            min_units = st.number_input("Minimum Units", min_value=1, value=1)
        with col4:
            allow_subs = st.checkbox("Allow Substitutes", value=True)
            
        facility_filter = st.text_input("Filter by Facility Name (optional)")
        
        if st.button("🔍 Search Inventory", type="primary"):
            with st.spinner("Searching inventory..."):
                res = find_inventory(blood_group=bg_filter, component_type=comp_filter, minimum_units=min_units, allow_substitutes=allow_subs)
                if res.get("status") == "success":
                    data = res.get("data", [])
                    if data:
                        df = pd.DataFrame(data)
                        if facility_filter:
                            df = df[df['facility_name'].str.contains(facility_filter, case=False, na=False)]
                        
                        from datetime import datetime, date
                        today = date.today()
                        
                        def compute_inventory_status(units):
                            if pd.isna(units): return "🟢 Healthy"
                            u = int(units)
                            if u > 20: return "🟢 Healthy"
                            elif u >= 6: return "🟡 Low"
                            else: return "🔴 Critical"
                        
                        def compute_expiry_status(val):
                            if pd.isna(val): return "🟢 Fresh"
                            try:
                                if isinstance(val, str):
                                    exp_date = datetime.strptime(val, '%Y-%m-%d').date()
                                else:
                                    exp_date = val
                                days_left = (exp_date - today).days
                                if days_left <= 3: return "🔴 Expires Soon"
                                elif days_left <= 7: return "🟡 Near Expiry"
                                return "🟢 Fresh"
                            except:
                                return "🟢 Fresh"

                        df['Inventory Status'] = df['units_available'].apply(compute_inventory_status)
                        df['Expiry Status'] = df['expiry_date'].apply(compute_expiry_status)

                        # Specify columns in required order
                        ordered_cols = [
                            'facility_name', 'facility_address', 'city', 'blood_group', 
                            'component_type', 'Inventory Status', 'units_available', 'reserved_units', 
                            'Expiry Status', 'collection_date', 'expiry_date', 'phone', 'contact_person'
                        ]
                        
                        display_df = df[ordered_cols].copy()
                        
                        # Rename columns
                        rename_dict = {
                            'facility_name': 'Facility',
                            'facility_address': 'Address',
                            'city': 'City',
                            'blood_group': 'Blood Group',
                            'component_type': 'Component',
                            'units_available': 'Available Units',
                            'reserved_units': 'Reserved Units',
                            'collection_date': 'Collection Date',
                            'expiry_date': 'Expiry Date',
                            'phone': 'Phone',
                            'contact_person': 'Contact Person'
                        }
                        display_df.rename(columns=rename_dict, inplace=True)
                        
                        # KPI Cards
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("🩸 Matching Records", len(display_df))
                        m2.metric("🟢 Healthy Stock", len(display_df[display_df['Inventory Status'] == "🟢 Healthy"]))
                        m3.metric("🟡 Low Stock", len(display_df[display_df['Inventory Status'] == "🟡 Low"]))
                        m4.metric("🔴 Critical Stock", len(display_df[display_df['Inventory Status'] == "🔴 Critical"]))
                        
                        st.markdown("---")
                        
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Collection Date": st.column_config.DateColumn("Collection Date", format="YYYY-MM-DD"),
                                "Expiry Date": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD"),
                            }
                        )
                        
                        with st.expander("Show Raw Data with IDs (for Reservations)"):
                            st.dataframe(df, use_container_width=True)
                            
                    else:
                        st.info("No matching inventory found.")
                else:
                    st.error(f"Search failed: {res.get('message')}")
                    
        st.markdown("---")
        st.subheader("Reserve Blood Units")
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            inv_id = st.number_input("Inventory ID", min_value=1, step=1)
        with col_res2:
            res_units = st.number_input("Units to Reserve", min_value=1, step=1)
            
        if st.button("🔒 Reserve Blood", type="primary"):
            with st.spinner("Reserving..."):
                r_res = reserve_units(inventory_id=inv_id, units=res_units)
                if r_res.get("status") == "success":
                    st.success(r_res.get("message"))
                else:
                    st.error(r_res.get("message"))

    # Tab 2: Expiry & Low Stock
    with tab2:
        from datetime import date
        today = date.today()
        
        st.subheader("Low Stock Alerts")
        
        with st.expander("⚠️ Inventory Alerts Guide"):
            st.markdown("""
**Healthy Stock**: Inventory > 20 units.
**Low Stock**: Inventory between 6 and 20 units. Monitor closely.
**Critical Stock**: Inventory ≤ 5 units. Immediate replenishment required.
            """)
        with st.spinner("Loading alerts..."):
            low_res = get_low_stock()
            if low_res.get("status") == "success":
                low_data = low_res.get("data", [])
                if low_data:
                    df_low = pd.DataFrame(low_data)
                    
                    def compute_low_stock_status(units):
                        if pd.isna(units): return "🟢 Healthy"
                        u = int(units)
                        if u > 20: return "🟢 Healthy"
                        elif u >= 6: return "🟡 Low"
                        else: return "🔴 Critical"
                        
                    df_low['Stock Status'] = df_low['units_available'].apply(compute_low_stock_status)
                    df_low.sort_values(by='units_available', ascending=True, inplace=True)
                    
                    # KPIs
                    l1, l2, l3 = st.columns(3)
                    l1.metric("🔴 Critical Inventory", len(df_low[df_low['Stock Status'] == '🔴 Critical']))
                    l2.metric("🟡 Low Stock", len(df_low[df_low['Stock Status'] == '🟡 Low']))
                    l3.metric("🟢 Healthy Stock", len(df_low[df_low['Stock Status'] == '🟢 Healthy']))
                    
                    # Formatting columns
                    df_low.rename(columns={
                        'facility_name': 'Facility',
                        'facility_address': 'Address',
                        'city': 'City',
                        'blood_group': 'Blood Group',
                        'component_type': 'Component',
                        'units_available': 'Available Units',
                        'minimum_threshold': 'Minimum Threshold',
                        'expiry_date': 'Expiry Date',
                        'phone': 'Phone'
                    }, inplace=True)
                    
                    ordered_low_cols = ['Facility', 'Address', 'City', 'Blood Group', 'Component', 'Available Units', 'Minimum Threshold', 'Stock Status', 'Expiry Date', 'Phone']
                    
                    # Ensure columns exist in case some data was missing
                    for col in ordered_low_cols:
                        if col not in df_low.columns:
                            df_low[col] = None
                            
                    st.dataframe(df_low[ordered_low_cols], use_container_width=True, hide_index=True)
                else:
                    st.success("No low-stock inventory found.")
            else:
                st.error("Failed to load low stock alerts.")
                
        st.markdown("---")
        st.subheader("Expiry Warnings (Next 7 Days)")
        exp_df = get_expiring_inventory(days=7)
        if not exp_df.empty:
            today_ts = pd.Timestamp.today().normalize()
            exp_df['Expiry Date'] = pd.to_datetime(exp_df['Expiry Date'], errors='coerce')
            exp_df['Days Remaining'] = (exp_df['Expiry Date'] - today_ts).dt.days
            
            def compute_exp_status(days):
                if pd.isna(days): return "🟢 Fresh"
                if days <= 0: return "🔴 Expires Today"
                elif days <= 3: return "🟠 1–3 Days"
                elif days <= 7: return "🟡 4–7 Days"
                return "🟢 Fresh"
                
            exp_df['Expiry Status'] = exp_df['Days Remaining'].apply(compute_exp_status)
            exp_df.sort_values(by='Expiry Date', ascending=True, inplace=True)
            
            # Format date for display
            exp_df['Expiry Date'] = exp_df['Expiry Date'].dt.strftime('%Y-%m-%d')
            
            e1, e2, e3 = st.columns(3)
            e1.metric("🔴 Expiring Today", len(exp_df[exp_df['Expiry Status'] == '🔴 Expires Today']))
            e2.metric("🟠 Within 3 Days", len(exp_df[exp_df['Expiry Status'] == '🟠 1–3 Days']))
            e3.metric("🟡 Within 7 Days", len(exp_df[exp_df['Expiry Status'] == '🟡 4–7 Days']))
            
            ordered_exp_cols = ['Facility', 'Address', 'City', 'Blood Group', 'Component', 'Available Units', 'Collection Date', 'Expiry Date', 'Days Remaining', 'Expiry Status']
            st.dataframe(exp_df[ordered_exp_cols], use_container_width=True, hide_index=True)
        else:
            st.success("No inventory nearing expiry.")

    # Tab 3: Reservations
    with tab3:
        st.subheader("Manage Active Reservations")
        
        with st.expander("Reservation Status Guide"):
            st.markdown("""
| Status | Meaning | Inventory Impact |
|--------|---------|------------------|
| 🟡 Pending | Blood request created. Inventory identified but not yet reserved. | Units remain available |
| 🟢 Active | Blood units have been reserved for a specific blood request. | Units unavailable to other requests |
| 🔵 Issued | Blood units have been issued for transfusion. | Inventory permanently deducted |
| ⚪ Released | Reservation cancelled. Reserved units returned to inventory. | Inventory restored |
| 🔴 Expired | Reservation timed out before issue. Reserved units automatically returned. | Inventory restored |

**Operational Workflow**
```text
Blood Request
        ↓
Reservation Created
        ↓
Active
        ↓
Issued / Released / Expired
```
""")
        
        r_df = get_active_reservations()
        if not r_df.empty:
            def format_res_status(status):
                if not isinstance(status, str): return status
                s = status.lower()
                if s == 'active': return '🟢 Active'
                if s == 'pending': return '🟡 Pending'
                if s == 'issued': return '🔵 Issued'
                if s == 'released': return '⚪ Released'
                if s == 'expired': return '🔴 Expired'
                if s == 'completed': return '🔵 Issued'
                return status
                
            r_df['Status'] = r_df['Status'].apply(format_res_status)
            
            # Format dates
            for col in ['Reservation Date', 'Reserved Until']:
                if col in r_df.columns:
                    r_df[col] = pd.to_datetime(r_df[col], errors='coerce').dt.strftime('%d %b %Y %I:%M %p')
            
            r1, r2, r3 = st.columns(3)
            r1.metric("🟢 Active Reservations", len(r_df[r_df['Status'] == '🟢 Active']))
            r2.metric("🔵 Issued", len(r_df[r_df['Status'] == '🔵 Issued']))
            r3.metric("⚪ Released", len(r_df[r_df['Status'] == '⚪ Released']))
            
            # Select specific columns
            res_cols = ['Reservation Date', 'Hospital', 'Hospital Address', 'Blood Request ID', 'Blood Group', 'Component', 'Reserved Units', 'Status', 'Reserved Until', 'Reserved By Agent']
            st.dataframe(r_df[[c for c in res_cols if c in r_df.columns]], use_container_width=True, hide_index=True)
        else:
            st.info("No active reservations.")
                    
        st.markdown("---")
        st.write("Release Reservation")
        rel_id = st.number_input("Blood Request ID to Release", min_value=1, step=1)
        if st.button("Release Reservation"):
            with st.spinner("Releasing..."):
                rel_res = release_reservation(request_id=rel_id)
                if rel_res.get("status") == "success":
                    st.success(rel_res.get("message"))
                    from frontend.utils.database import fetch_data
                    fetch_data.clear()
                    st.rerun()
                else:
                    st.error(rel_res.get("message"))
