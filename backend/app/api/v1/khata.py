import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_admin
from app.db.supabase import get_supabase_admin_client
from app.services.khata_service import KhataService

router = APIRouter(prefix="/khata", tags=["Khata"])
logger = logging.getLogger(__name__)

_khata_service = KhataService()


class KhataAddRequest(BaseModel):
    store_id: str
    text: str


@router.post("/add")
async def add_khata_entry(body: KhataAddRequest) -> dict:
    """
    Parses a free-text Khata entry (Hindi/English) via SLM and updates the ledger.
    Example: "Ramesh ne 200 diya" → PAYMENT_RECEIVED ₹200 for Ramesh.
    """
    result = await _khata_service.parse_khata_record(body.text, body.store_id)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@router.get("/{store_id}")
async def get_khata(store_id: str) -> dict:
    """Returns all khata records for a store with customer details."""
    db = get_supabase_admin_client()
    res = (
        db.table("khata_ledger")
        .select("*, customers(name, phone)")
        .eq("customers.store_id", store_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return {"store_id": store_id, "records": res.data}
