from app.db.supabase import get_supabase_admin_client
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_test_data():
    db = get_supabase_admin_client()
    
    # 1. Add Stores
    test_numbers = ["919534177010", "919981909017", "919109298199"]
    store_ids = []
    
    logger.info("Setting up Stores...")
    for i, num in enumerate(test_numbers):
        try:
            # Check if exists
            existing = db.table("stores").select("id").eq("contact_phone", num).execute()
            if not existing.data:
                res = db.table("stores").insert({
                    "name": f"Test Store {i+1}",
                    "contact_phone": num,
                    "owner_name": "Pratul"
                }).execute()
                store_id = res.data[0]["id"]
                logger.info(f"Created store for {num}")
            else:
                store_id = existing.data[0]["id"]
                logger.info(f"Store for {num} already exists")
            store_ids.append(store_id)
        except Exception as e:
            logger.error(f"Error creating store for {num}: {e}")

    # 2. Add Sample SKUs for each store
    logger.info("\nSetting up SKUs...")
    for store_id in store_ids:
        skus = [
            {"name": "Milk", "store_id": store_id},
            {"name": "Bread", "store_id": store_id},
            {"name": "Sugar", "store_id": store_id}
        ]
        for sku in skus:
            try:
                # Check if exists
                existing = db.table("skus").select("id").eq("name", sku["name"]).eq("store_id", store_id).execute()
                if not existing.data:
                    res = db.table("skus").insert(sku).execute()
                    sku_id = res.data[0]["id"]
                    # Also add initial inventory
                    db.table("inventory").insert({"sku_id": sku_id, "stock_level": 10}).execute()
                    logger.info(f"Created SKU {sku['name']} for store {store_id}")
                else:
                    logger.info(f"SKU {sku['name']} already exists for store {store_id}")
            except Exception as e:
                logger.error(f"Error creating SKU {sku['name']}: {e}")

    # 3. Add Sample Customers for Khata
    logger.info("\nSetting up Customers...")
    for store_id in store_ids:
        customers = [
            {"name": "Pratul", "phone": "919534177010", "store_id": store_id},
            {"name": "Rishabh", "phone": "919981909017", "store_id": store_id},
            {"name": "Rajveer", "phone": "919109298199", "store_id": store_id}
        ]
        for cust in customers:
            try:
                existing = db.table("customers").select("id").ilike("name", cust["name"]).eq("store_id", store_id).execute()
                if not existing.data:
                    res = db.table("customers").insert(cust).execute()
                    cust_id = res.data[0]["id"]
                    logger.info(f"Created Customer {cust['name']} for store {store_id}")
                else:
                    logger.info(f"Customer {cust['name']} already exists for store {store_id}")
            except Exception as e:
                logger.error(f"Error creating customer {cust['name']}: {e}")

    logger.info("\nTest setup complete!")

if __name__ == "__main__":
    setup_test_data()
