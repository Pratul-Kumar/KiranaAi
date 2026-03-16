import logging
from typing import Optional

from app.db.supabase import get_supabase_admin_client
from app.models.schemas import AIIntentResponse
from app.services.demand_engine import DemandSensingEngine

logger = logging.getLogger(__name__)


class InventoryOrchestrator:
    """Manages stock updates and reorder logic with deterministic SKU matching."""

    def __init__(self) -> None:
        self.db = get_supabase_admin_client()
        self.demand_engine = DemandSensingEngine()

    async def _resolve_sku_id(self, sku_name: str, store_id: str) -> Optional[str]:
        """Deterministic SKU matching: exact match first, then fuzzy."""
        if not sku_name:
            return None

        sku_res = self.db.table("skus").select("id").eq("name", sku_name).eq("store_id", store_id).execute()
        if sku_res.data:
            return sku_res.data[0]["id"]

        sku_res = self.db.table("skus").select("id").ilike("name", f"%{sku_name}%").eq("store_id", store_id).execute()
        if sku_res.data:
            return sku_res.data[0]["id"]

        return None

    async def update_stock(self, ai_result: AIIntentResponse, store_id: str) -> dict:
        """Updates inventory levels based on structured AI output."""
        sku_name = ai_result.sku
        qty = ai_result.quantity or 1.0

        sku_id = await self._resolve_sku_id(sku_name, store_id)

        if not sku_id:
            logger.info(f"SKU '{sku_name}' not found. Logging as lost sale.")
            self.db.table("lost_sales").insert({
                "store_id": store_id,
                "sku_name": sku_name,
                "requested_qty": qty,
                "detected_at": "now()",
            }).execute()
            return {"status": "lost_sale_logged", "sku_name": sku_name}

        inv_res = self.db.table("inventory").select("stock_level").eq("sku_id", sku_id).execute()
        current_stock = float(inv_res.data[0]["stock_level"]) if inv_res.data else 0.0
        new_stock = current_stock + qty

        self.db.table("inventory").upsert({
            "sku_id": sku_id,
            "stock_level": new_stock,
            "last_updated": "now()",
        }).execute()

        alert_triggered = await self.demand_engine.check_threshold_and_alert(sku_id)

        return {
            "status": "updated",
            "sku_id": sku_id,
            "new_stock": new_stock,
            "alert_triggered": alert_triggered,
            "confidence": ai_result.confidence,
        }

