import os

import streamlit as st
import requests

st.set_page_config(
    page_title="ZnShop Admin",
    page_icon="🏪",
    layout="wide",
)

API_BASE = os.environ.get("ZNSHOP_API_URL", "http://localhost:8000/api/v1")


# ─── Session State ────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None


def _headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def _api(method: str, path: str, **kwargs) -> dict | None:
    try:
        r = getattr(requests, method)(f"{API_BASE}{path}", headers=_headers(), **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


# ─── Login ────────────────────────────────────────────────────────
if not st.session_state.token:
    st.title("🏪 ZnShop Admin — Login")
    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                r = requests.post(f"{API_BASE}/admin/login", json={"email": email, "password": password})
                if r.status_code == 200:
                    st.session_state.token = r.json()["access_token"]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            except Exception as e:
                st.error(f"Cannot reach backend: {e}")
    st.stop()


# ─── Sidebar ──────────────────────────────────────────────────────
st.sidebar.title("🏪 ZnShop Admin")
section = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "🏬 Stores", "🚚 Vendors", "📦 Inventory", "📔 Khata", "🔔 Alerts", "📢 Broadcast"],
)
if st.sidebar.button("Logout"):
    st.session_state.token = None
    st.rerun()

# ─── Dashboard Overview ───────────────────────────────────────────
if section == "📊 Dashboard":
    st.title("📊 Dashboard Overview")
    col1, col2, col3 = st.columns(3)

    stores = _api("get", "/admin/stores")
    vendors = _api("get", "/admin/vendors")
    alerts = _api("get", "/admin/alerts")

    col1.metric("Total Stores", len(stores.get("stores", [])) if stores else "—")
    col2.metric("Total Vendors", len(vendors.get("vendors", [])) if vendors else "—")
    col3.metric("Demand Alerts", len(alerts.get("alerts", [])) if alerts else "—")

    if alerts and alerts.get("alerts"):
        st.subheader("Latest Demand Alerts")
        st.dataframe(alerts["alerts"][:10], use_container_width=True)

# ─── Stores ───────────────────────────────────────────────────────
elif section == "🏬 Stores":
    st.title("🏬 Store Management")

    with st.expander("➕ Add New Store"):
        with st.form("add_store"):
            name = st.text_input("Store Name")
            phone = st.text_input("Owner Phone (e.g. 919876543210)")
            owner = st.text_input("Owner Name")
            address = st.text_input("Address (optional)")
            if st.form_submit_button("Create Store"):
                result = _api("post", "/admin/stores", json={
                    "name": name, "contact_phone": phone,
                    "owner_name": owner, "address": address or None,
                })
                if result:
                    st.success(f"Store '{name}' created!")
                    st.rerun()

    data = _api("get", "/admin/stores")
    if data:
        st.subheader(f"All Stores ({len(data['stores'])})")
        st.dataframe(data["stores"], use_container_width=True)

# ─── Vendors ──────────────────────────────────────────────────────
elif section == "🚚 Vendors":
    st.title("🚚 Vendor Management")

    with st.expander("➕ Add New Vendor"):
        with st.form("add_vendor"):
            v_name = st.text_input("Vendor Name")
            v_phone = st.text_input("Phone (e.g. 919876543210)")
            v_cat = st.text_input("Category (e.g. dairy, beverages)")
            if st.form_submit_button("Create Vendor"):
                result = _api("post", "/admin/vendors", json={
                    "name": v_name, "phone": v_phone, "category": v_cat,
                })
                if result:
                    st.success(f"Vendor '{v_name}' created!")
                    st.rerun()

    with st.expander("🔗 Assign Vendor to Store"):
        stores_data = _api("get", "/admin/stores")
        vendors_data = _api("get", "/admin/vendors")
        if stores_data and vendors_data:
            store_map = {s["name"]: s["id"] for s in stores_data["stores"]}
            vendor_map = {v["name"]: v["id"] for v in vendors_data["vendors"]}
            with st.form("assign_vendor"):
                sel_store = st.selectbox("Store", list(store_map.keys()))
                sel_vendor = st.selectbox("Vendor", list(vendor_map.keys()))
                if st.form_submit_button("Assign"):
                    result = _api("post", "/admin/assign-vendor", json={
                        "store_id": store_map[sel_store],
                        "vendor_id": vendor_map[sel_vendor],
                    })
                    if result:
                        st.success(f"Assigned {sel_vendor} → {sel_store}")

    data = _api("get", "/admin/vendors")
    if data:
        st.subheader(f"All Vendors ({len(data['vendors'])})")
        st.dataframe(data["vendors"], use_container_width=True)

# ─── Inventory ────────────────────────────────────────────────────
elif section == "📦 Inventory":
    st.title("📦 Inventory")
    stores_data = _api("get", "/admin/stores")
    if stores_data and stores_data["stores"]:
        store_map = {s["name"]: s["id"] for s in stores_data["stores"]}
        sel = st.selectbox("Select Store", list(store_map.keys()))
        data = _api("get", f"/admin/inventory/{store_map[sel]}")
        if data:
            st.subheader(f"Inventory — {sel}")
            st.dataframe(data.get("inventory", []), use_container_width=True)

# ─── Khata ────────────────────────────────────────────────────────
elif section == "📔 Khata":
    st.title("📔 Khata Records")
    stores_data = _api("get", "/admin/stores")
    if stores_data and stores_data["stores"]:
        store_map = {s["name"]: s["id"] for s in stores_data["stores"]}
        sel = st.selectbox("Select Store", list(store_map.keys()))
        data = _api("get", f"/admin/khata/{store_map[sel]}")
        if data:
            st.subheader(f"Khata — {sel}")
            st.dataframe(data.get("khata", []), use_container_width=True)

# ─── Alerts ───────────────────────────────────────────────────────
elif section == "🔔 Alerts":
    st.title("🔔 Demand Alerts")
    data = _api("get", "/admin/alerts")
    if data:
        st.dataframe(data.get("alerts", []), use_container_width=True)

# ─── Broadcast ────────────────────────────────────────────────────
elif section == "📢 Broadcast":
    st.title("📢 Broadcast Message")
    with st.form("broadcast"):
        msg = st.text_area("Message", height=120)
        send_all = st.checkbox("Send to ALL stores", value=True)
        if st.form_submit_button("Send Broadcast"):
            payload = {"message": msg, "store_ids": None if send_all else []}
            result = _api("post", "/admin/broadcast", json=payload)
            if result:
                st.success(f"Sent: {result.get('sent', 0)} / Failed: {result.get('failed', 0)}")
