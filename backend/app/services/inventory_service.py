import logging
from typing import Optional

from backend.app.db.supabase import get_supabase_admin_client
from backend.app.models.schemas import AIIntentResponse
from backend.app.models.demand_engine import DemandSensingEngine

logger = logging.getLogger(__name__)


class InventoryOrchestrator:
    """Manages stock updates and reorder logic with deterministic SKU matching."""

    def __init__(self) -> None:
        self._db = None
        self._demand_engine = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_supabase_admin_client()
        return self._db

    @property
    def demand_engine(self) -> DemandSensingEngine:
        if self._demand_engine is None:
            self._demand_engine = DemandSensingEngine()
        return self._demand_engine

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
        try:
            sku_id = await self._resolve_sku_id(sku_name, store_id)

            if not sku_id:
                logger.info("SKU '%s' not found for store %s; logging lost sale.", sku_name, store_id)
                self.db.table("lost_sales").insert({
                    "store_id": store_id,
                    "sku_name": sku_name,
                    "requested_qty": qty,
                    "detected_at": "now()",
                }).execute()
                return {"status": "not_found", "sku_name": sku_name, "detail": "SKU not found; logged as lost sale"}

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
        except Exception as exc:
            logger.exception("Inventory orchestrator update failed: %s", exc)
            return {"status": "error", "detail": str(exc)}

