"""
scripts/seed_demo_data.py — Larger demo dataset (6 stores, 8 vendors).
Run from project root:  python scripts/seed_demo_data.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from app.db.supabase import get_supabase_admin_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

db = get_supabase_admin_client()

STORES = [
    {"name": "Ravi Kirana",          "contact_phone": "919534170001", "owner_name": "Ravi Kumar",       "address": "Sector 12, Delhi"},
    {"name": "Gupta Store",          "contact_phone": "919534170002", "owner_name": "Suresh Gupta",     "address": "MG Road, Lucknow"},
    {"name": "Patel Mart",           "contact_phone": "919534170003", "owner_name": "Amrit Patel",      "address": "CG Road, Ahmedabad"},
    {"name": "Lakshmi Store",        "contact_phone": "919534170004", "owner_name": "Lakshmi Devi",     "address": "Anna Nagar, Chennai"},
    {"name": "Verma General Store",  "contact_phone": "919534170005", "owner_name": "Rajesh Verma",     "address": "Connaught Place, Delhi"},
    {"name": "Sai Kirana",           "contact_phone": "919534170006", "owner_name": "Sai Baba",         "address": "Banjara Hills, Hyderabad"},
]

VENDORS = [
    {"name": "Milk Supplier",        "phone": "919534171001", "category": "dairy"},
    {"name": "Maggi Distributor",    "phone": "919534171002", "category": "snacks"},
    {"name": "Rice Supplier",        "phone": "919534171003", "category": "grains"},
    {"name": "Tea Supplier",         "phone": "919534171004", "category": "beverages"},
    {"name": "Oil Supplier",         "phone": "919534171005", "category": "oils"},
    {"name": "Biscuit Supplier",     "phone": "919534171006", "category": "snacks"},
    {"name": "Soap Distributor",     "phone": "919534171007", "category": "personal_care"},
    {"name": "Cold Drink Supplier",  "phone": "919534171008", "category": "beverages"},
]

SKUS = [
    {"name": "Milk",        "category_path": "dairy"},
    {"name": "Bread",       "category_path": "bakery"},
    {"name": "Sugar",       "category_path": "grains"},
    {"name": "Maggi",       "category_path": "snacks"},
    {"name": "Tea",         "category_path": "beverages"},
    {"name": "Rice",        "category_path": "grains"},
    {"name": "Oil",         "category_path": "oils"},
    {"name": "Biscuits",    "category_path": "snacks"},
    {"name": "Soap",        "category_path": "personal_care"},
    {"name": "Cold Drink",  "category_path": "beverages"},
]

CUSTOMERS = [
    {"name": "Ramesh", "suffix": "1"},
    {"name": "Priya",  "suffix": "2"},
    {"name": "Arjun",  "suffix": "3"},
    {"name": "Sunita", "suffix": "4"},
]


def _upsert(table: str, data: dict, keys: list, return_col: str = "id") -> dict | None:
    q = db.table(table).select(return_col)
    for k in keys:
        q = q.eq(k, data[k])
    existing = q.execute()
    if existing.data:
        log.info("  [skip] %-20s %s", table, " | ".join(str(data[k]) for k in keys))
        return existing.data[0]
    res = db.table(table).insert(data).execute()
    log.info("  [ok]   %-20s %s", table, " | ".join(str(data[k]) for k in keys))
    return res.data[0] if res.data else None


def seed():
    log.info("=== Seeding ZnShop Demo Data ===\n")

    log.info("── Vendors (%d)──", len(VENDORS))
    vendor_ids = []
    for v in VENDORS:
        rec = _upsert("vendors", v, ["phone"])
        if rec:
            vendor_ids.append(rec["id"])

    log.info("\n── Stores (%d) ──", len(STORES))
    for i, store_data in enumerate(STORES):
        store = _upsert("stores", store_data, ["contact_phone"])
        if not store:
            continue
        store_id = store["id"]

        for sku_data in SKUS:
            sku = _upsert("skus", {**sku_data, "store_id": store_id}, ["name", "store_id"])
            if sku:
                _upsert("inventory", {"sku_id": sku["id"], "stock_level": 50 + i * 5}, ["sku_id"], "sku_id")

        for j, c in enumerate(CUSTOMERS):
            phone = f"9195341720{i:02d}{j}"
            cust = _upsert("customers", {**c, "phone": phone, "store_id": store_id}, ["phone", "store_id"])
            if cust:
                _upsert("khata_ledger", {"customer_id": cust["id"], "balance": 0, "lead_score": 0}, ["customer_id"], "customer_id")

        for vid in vendor_ids:
            _upsert("store_vendors", {"store_id": store_id, "vendor_id": vid}, ["store_id", "vendor_id"], "store_id")

    log.info("\n=== Done — %d stores | %d vendors | %d SKUs/store | %d customers/store ===",
             len(STORES), len(VENDORS), len(SKUS), len(CUSTOMERS))


if __name__ == "__main__":
    seed()
