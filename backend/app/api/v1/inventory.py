import logging

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from backend.app.core.security import get_current_admin
from backend.app.db.supabase import get_supabase_admin_client
from backend.app.models.schemas import InventoryUpdateRequest

router = APIRouter(prefix="/inventory", tags=["Inventory"])
logger = logging.getLogger(__name__)


@router.post("/update", dependencies=[Depends(get_current_admin)])
async def update_inventory(body: InventoryUpdateRequest) -> dict:
    try:
        db = get_supabase_admin_client()

        sku_res = (
            db.table("skus")
            .select("id")
            .ilike("name", f"%{body.sku_name}%")
            .eq("store_id", body.store_id)
            .execute()
        )
        if not sku_res.data:
            raise HTTPException(status_code=404, detail=f"SKU '{body.sku_name}' not found in store {body.store_id}")

        sku_id = sku_res.data[0]["id"]

        inv_res = db.table("inventory").select("stock_level").eq("sku_id", sku_id).execute()
        current = float(inv_res.data[0]["stock_level"]) if inv_res.data else 0.0
        new_stock = current + body.quantity_delta

        db.table("inventory").upsert({
            "sku_id": sku_id,
            "stock_level": new_stock,
            "last_updated": "now()",
        }).execute()

        logger.info("Inventory updated | store_id=%s sku=%s delta=%s new_stock=%s", body.store_id, body.sku_name, body.quantity_delta, new_stock)
        return {"status": "updated", "sku_id": sku_id, "new_stock": new_stock}
    except HTTPException:
        raise
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Inventory update API error: %s", err or str(exc))
        raise HTTPException(status_code=500, detail="Inventory update failed")
    except Exception as exc:
        logger.exception("Inventory update failed: %s", exc)
        raise HTTPException(status_code=500, detail="Inventory update failed")


@router.get("/{store_id}")
async def get_inventory(store_id: str) -> dict:
    try:
        db = get_supabase_admin_client()
        res = (
            db.table("skus")
            .select("id, name, category_path, inventory(stock_level, last_updated)")
            .eq("store_id", store_id)
            .execute()
        )
        return {"store_id": store_id, "skus": res.data or []}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Get inventory API error: %s", err or str(exc))
        raise HTTPException(status_code=500, detail="Get inventory failed")
    except Exception as exc:
        logger.exception("Get inventory failed: %s", exc)
        raise HTTPException(status_code=500, detail="Get inventory failed")
