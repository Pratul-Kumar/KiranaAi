"""
scripts/seed_data.py — Populates ZnShop with demo stores, vendors, SKUs, inventory, and customers.

Run from the project root:
    python scripts/seed_data.py
"""
import logging
import sys
import os

# allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from backend.app.db.supabase import get_supabase_admin_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

db = get_supabase_admin_client()

# demo stores
STORES = [
    {"name": "Ravi Kirana",          "contact_phone": "919534177001", "owner_name": "Ravi Kumar",   "address": "Sector 12, Delhi"},
    {"name": "Gupta General Store",  "contact_phone": "919534177002", "owner_name": "Suresh Gupta", "address": "MG Road, Lucknow"},
    {"name": "Lakshmi Stores",       "contact_phone": "919534177003", "owner_name": "Lakshmi Devi", "address": "Anna Nagar, Chennai"},
    {"name": "Patel Mart",           "contact_phone": "919534177004", "owner_name": "Amrit Patel",  "address": "CG Road, Ahmedabad"},
]

# demo vendors
VENDORS = [
    {"name": "Milk Supplier",       "phone": "919534178001", "category": "dairy"},
    {"name": "Maggi Distributor",   "phone": "919534178002", "category": "snacks"},
    {"name": "Rice Supplier",       "phone": "919534178003", "category": "grains"},
    {"name": "Tea Supplier",         "phone": "919534178004", "category": "beverages"},
    {"name": "Biscuit Distributor", "phone": "919534178005", "category": "snacks"},
    {"name": "Oil Supplier",         "phone": "919534178006", "category": "oils"},
]

# demo SKUs
SKUS_PER_STORE = [
    {"name": "Milk",     "category_path": "dairy"},
    {"name": "Bread",    "category_path": "bakery"},
    {"name": "Sugar",    "category_path": "grains"},
    {"name": "Maggi",    "category_path": "snacks"},
    {"name": "Tea",      "category_path": "beverages"},
    {"name": "Rice",     "category_path": "grains"},
    {"name": "Biscuits", "category_path": "snacks"},
    {"name": "Oil",      "category_path": "oils"},
]

# demo customers
CUSTOMERS_PER_STORE = [
    {"name": "Ramesh", "phone": "919534179001"},
    {"name": "Priya",  "phone": "919534179002"},
    {"name": "Arjun",  "phone": "919534179003"},
]


def _upsert(table: str, data: dict, unique_keys: list[str], return_col: str = "id") -> dict | None:
    """Insert if not exists; skip silently if already present."""
    q = db.table(table).select(return_col)
    for k in unique_keys:
        q = q.eq(k, data[k])
    existing = q.execute()
    if existing.data:
        logger.info(f"  [skip] {table}: {' | '.join(str(data[k]) for k in unique_keys)} already exists")
        return existing.data[0]
    res = db.table(table).insert(data).execute()
    logger.info(f"  [ok]   {table}: created {' | '.join(str(data[k]) for k in unique_keys)}")
    return res.data[0] if res.data else None


def seed() -> None:
    logger.info("=== Seeding ZnShop Demo Data ===\n")

    # vendors
    logger.info("── Vendors ──")
    vendor_id_map: dict[str, str] = {}  # category to vendor id
    for v in VENDORS:
        record = _upsert("vendors", v, ["phone"])
        if record:
            vendor_id_map[v["category"]] = record["id"]

    # stores and related data
    logger.info("\n── Stores ──")
    for store_data in STORES:
        store = _upsert("stores", store_data, ["contact_phone"])
        if not store:
            continue
        store_id = store["id"]

        # SKUs and inventory
        logger.info(f"\n  SKUs for {store_data['name']}")
        for sku_data in SKUS_PER_STORE:
            sku_payload = {**sku_data, "store_id": store_id}
            sku = _upsert("skus", sku_payload, ["name", "store_id"])
            if sku:
                _upsert("inventory", {"sku_id": sku["id"], "stock_level": 50}, ["sku_id"], return_col="sku_id")

        # customers and khata
        logger.info(f"  Customers for {store_data['name']}")
        for cust_data in CUSTOMERS_PER_STORE:
            # keep phone unique per store
            store_idx = STORES.index(store_data)
            phone = cust_data["phone"][:-1] + str(store_idx + 1)
            cust_payload = {**cust_data, "phone": phone, "store_id": store_id}
            cust = _upsert("customers", cust_payload, ["phone", "store_id"])
            if cust:
                _upsert(
                    "khata_ledger",
                    {"customer_id": cust["id"], "balance": 0, "lead_score": 0},
                    ["customer_id"],
                    return_col="customer_id"
                )

        # assign vendors to store
        for vendor_id in vendor_id_map.values():
            _upsert("store_vendors", {"store_id": store_id, "vendor_id": vendor_id}, ["store_id", "vendor_id"], return_col="store_id")

    logger.info("\n=== Seeding Complete ===")
    logger.info(f"Stores: {len(STORES)} | Vendors: {len(VENDORS)} | SKUs/store: {len(SKUS_PER_STORE)} | Customers/store: {len(CUSTOMERS_PER_STORE)}")


if __name__ == "__main__":
    seed()
