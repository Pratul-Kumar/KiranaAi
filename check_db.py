import os
import sys
from dotenv import load_dotenv

# Ensure we're in the right directory to load the app
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.db.supabase import get_supabase_admin_client

def check_db():
    print("Connecting to Supabase...")
    try:
        db = get_supabase_admin_client()
        # Raw SQL to list tables via PostgREST RPC if enabled, or just try to select from skus
        try:
            res = db.table("skus").select("id").limit(1).execute()
            print("Table 'skus' exists.")
        except Exception as e:
            print(f"Table 'skus' check failed: {e}")
            
        try:
            res = db.table("inventory").select("sku_id").limit(1).execute()
            print("Table 'inventory' exists.")
        except Exception as e:
            print(f"Table 'inventory' check failed: {e}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_db()
