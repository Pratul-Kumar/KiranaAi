from app.db.supabase import get_supabase_admin_client
from app.services.demand_engine import DemandSensingEngine
from app.schemas.ai_schemas import AIIntentResponse
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class InventoryOrchestrator:
    """Manages stock updates and reorder logic with deterministic SKU matching."""
    
    def __init__(self):
        self.db = get_supabase_admin_client()
        self.demand_engine = DemandSensingEngine()
        # Simple in-memory cache for demo; use Redis in production
        self.sku_cache = {}

    async def _resolve_sku_id(self, sku_name: str, store_id: str) -> Optional[str]:
        """Deterministic SKU matching layer."""
        if not sku_name:
            return None
            
        cache_key = f"{store_id}:{sku_name.lower()}"
        if cache_key in self.sku_cache:
            return self.sku_cache[cache_key]

        # 1. Exact Match
        sku_res = self.db.table("skus").select("id").eq("name", sku_name).eq("store_id", store_id).execute()
        if sku_res.data:
            sku_id = sku_res.data[0]["id"]
            self.sku_cache[cache_key] = sku_id
            return sku_id

        # 2. Fuzzy Match (ilike)
        sku_res = self.db.table("skus").select("id").ilike("name", f"%{sku_name}%").eq("store_id", store_id).execute()
        if sku_res.data:
            sku_id = sku_res.data[0]["id"]
            self.sku_cache[cache_key] = sku_id
            return sku_id

        # 3. Future: Semantic search using embeddings should be here
        
        return None

    async def update_stock(self, ai_result: AIIntentResponse, store_id: str):
        """Updates inventory levels based on structured AI output."""
        sku_name = ai_result.sku
        qty = ai_result.quantity or 1.0
        
        sku_id = await self._resolve_sku_id(sku_name, store_id)
        
        if not sku_id:
            logger.info(f"SKU {sku_name} not found. Logging as potential lost sale.")
            self.db.table("lost_sales").insert({
                "store_id": store_id,
                "sku_name": sku_name,
                "requested_qty": qty,
                "detected_at": "now()"
            }).execute()
            return {"status": "lost_sale_logged", "sku_name": sku_name}

        # 2. Update Inventory
        inv_res = self.db.table("inventory").select("stock_level").eq("sku_id", sku_id).execute()
        current_stock = inv_res.data[0]["stock_level"] if inv_res.data else 0
        
        # Change is handled by the intent router (positive for stock_update, negative for reorder/sale)
        # For simplicity, we assume intentional update here
        new_stock = float(current_stock) + qty
        
        self.db.table("inventory").upsert({
            "sku_id": sku_id,
            "stock_level": new_stock,
            "last_updated": "now()"
        }).execute()

        # 3. Trigger asynchronous demand/alert check
        alert_triggered = await self.demand_engine.check_threshold_and_alert(sku_id)
        
        return {
            "status": "updated",
            "sku_id": sku_id,
            "new_stock": new_stock,
            "alert_triggered": alert_triggered,
            "confidence": ai_result.confidence
        }
