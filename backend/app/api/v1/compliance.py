from fastapi import APIRouter, HTTPException, Depends
from app.db.supabase import get_supabase_admin_client
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    """
    Compliance: Hard delete customer data upon request.
    Logs action to audit_logs.
    """
    db = get_supabase_admin_client()
    
    # 1. Log the audit event first
    db.table("audit_logs").insert({
        "action": "DELETE_CUSTOMER",
        "table_name": "customers",
        "record_id": customer_id,
        "details": {"reason": "User request for data deletion"}
    }).execute()
    
    # 2. Perform deletion
    res = db.table("customers").delete().eq("id", customer_id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    return {"status": "deleted", "customer_id": customer_id}

@router.post("/consent/{customer_id}")
async def update_consent(customer_id: str, consent: bool):
    """Update GDPR/Consent flag."""
    db = get_supabase_admin_client()
    db.table("customers").update({"consent_flag": consent}).eq("id", customer_id).execute()
    return {"status": "consent_updated", "customer_id": customer_id}
