import logging

from fastapi import APIRouter, Query

from src.db.supabase import get_supabase_client

router = APIRouter(prefix="/alerts", tags=["Alerts"])
logger = logging.getLogger(__name__)


@router.get("")
async def get_alerts(limit: int = Query(50, ge=1, le=200)) -> dict:
    """
    Returns the latest demand signals / alerts.
    Public endpoint — no authentication required.
    """
    db = get_supabase_client()
    res = (
        db.table("demand_signals")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    logger.info(f"GET /alerts — returned {len(res.data)} records")
    return {"alerts": res.data}
