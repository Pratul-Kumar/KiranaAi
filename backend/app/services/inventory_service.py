from app.db.supabase import get_supabase_admin_client
from app.services.demand_engine import DemandSensingEngine
import logging

logger = logging.getLogger(__name__)

class InventoryOrchestrator:
    """Manages stock updates, reorder logic, and supplier order drafting."""
    
    def __init__(self):
        self.db = get_supabase_admin_client()
        self.demand_engine = DemandSensingEngine()

    async def update_stock(self, sku_name: str, quantity_change: float, store_id: str):
        """Updates inventory levels based on SKU name (SLM extracted)."""
        # 1. Resolve SKU ID from name (Fuzzy lookup)
        # Try exact match first, then ilike
        sku_res = self.db.table("skus").select("id").eq("name", sku_name).eq("store_id", store_id).execute()
        
        if not sku_res.data:
            sku_res = self.db.table("skus").select("id").ilike("name", f"%{sku_name}%").eq("store_id", store_id).execute()
        
        if not sku_res.data:
            logger.info(f"SKU {sku_name} not found. Logging as potential lost sale.")
            self.db.table("lost_sales").insert({
                "store_id": store_id,
                "sku_name": sku_name,
                "requested_qty": quantity_change,
                "detected_at": "now()"
            }).execute()
            return {"status": "lost_sale_logged", "sku_name": sku_name}

        sku_id = sku_res.data[0]["id"]

        # 2. Update Inventory
        inv_res = self.db.table("inventory").select("stock_level").eq("sku_id", sku_id).execute()
        current_stock = inv_res.data[0]["stock_level"] if inv_res.data else 0
        new_stock = float(current_stock) + quantity_change
        
        self.db.table("inventory").upsert({
            "sku_id": sku_id,
            "stock_level": new_stock,
            "last_updated": "now()"
        }).execute()

        # 3. Check for low-stock or high-demand alerts
        alert_triggered = await self.demand_engine.check_threshold_and_alert(sku_id)
        
        return {
            "status": "updated",
            "sku_id": sku_id,
            "new_stock": new_stock,
            "alert_triggered": alert_triggered
        }

    async def log_lost_sale(self, sku_name: str, quantity: float, store_id: str):
        """Manually log a lost sale event."""
        self.db.table("lost_sales").insert({
            "store_id": store_id,
            "sku_name": sku_name,
            "requested_qty": quantity
        }).execute()
        return {"status": "lost_sale_logged"}
