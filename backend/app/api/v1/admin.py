import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import (
    create_access_token,
    get_current_admin,
    verify_password,
)
from app.core.config import get_settings
from app.db.supabase import get_supabase_admin_client
from app.models.schemas import (
    AdminLoginRequest,
    AssignVendorRequest,
    BroadcastRequest,
    KhataAddRequest,
    StoreCreate,
    TokenResponse,
    VendorCreate,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def admin_login(body: AdminLoginRequest) -> TokenResponse:
    if body.email != settings.ADMIN_EMAIL:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": body.email})
    return TokenResponse(access_token=token)


@router.post("/stores", dependencies=[Depends(get_current_admin)])
async def create_store(body: StoreCreate) -> dict:
    db = get_supabase_admin_client()
    res = db.table("stores").insert(body.model_dump(exclude_none=True)).execute()
    return {"status": "created", "store": res.data[0] if res.data else {}}


@router.get("/stores", dependencies=[Depends(get_current_admin)])
async def list_stores() -> dict:
    db = get_supabase_admin_client()
    res = db.table("stores").select("*").order("created_at", desc=True).execute()
    return {"stores": res.data}


@router.post("/vendors", dependencies=[Depends(get_current_admin)])
async def create_vendor(body: VendorCreate) -> dict:
    db = get_supabase_admin_client()
    res = db.table("vendors").insert(body.model_dump()).execute()
    return {"status": "created", "vendor": res.data[0] if res.data else {}}


@router.get("/vendors", dependencies=[Depends(get_current_admin)])
async def list_vendors() -> dict:
    db = get_supabase_admin_client()
    res = db.table("vendors").select("*").order("name").execute()
    return {"vendors": res.data}


@router.post("/assign-vendor", dependencies=[Depends(get_current_admin)])
async def assign_vendor(body: AssignVendorRequest) -> dict:
    db = get_supabase_admin_client()
    res = db.table("store_vendors").upsert({
        "store_id": body.store_id,
        "vendor_id": body.vendor_id,
    }).execute()
    return {"status": "assigned"}


@router.get("/inventory/{store_id}", dependencies=[Depends(get_current_admin)])
async def get_store_inventory(store_id: str) -> dict:
    db = get_supabase_admin_client()
    res = (
        db.table("inventory")
        .select("*, skus(name, category_path)")
        .eq("skus.store_id", store_id)
        .execute()
    )
    return {"store_id": store_id, "inventory": res.data}


@router.get("/khata/{store_id}", dependencies=[Depends(get_current_admin)])
async def get_khata(store_id: str) -> dict:
    db = get_supabase_admin_client()
    res = (
        db.table("khata_ledger")
        .select("*, customers(name, phone)")
        .eq("customers.store_id", store_id)
        .execute()
    )
    return {"store_id": store_id, "khata": res.data}


@router.get("/alerts", dependencies=[Depends(get_current_admin)])
async def get_alerts() -> dict:
    db = get_supabase_admin_client()
    res = (
        db.table("demand_signals")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"alerts": res.data}


@router.post("/khata/add", dependencies=[Depends(get_current_admin)])
async def add_khata_record(body: KhataAddRequest) -> dict:
    """Add a khata (ledger) record — credit given or payment received."""
    db = get_supabase_admin_client()

    cust_res = (
        db.table("customers")
        .select("id")
        .eq("id", body.customer_id)
        .execute()
    )
    if not cust_res.data:
        raise HTTPException(status_code=404, detail=f"Customer '{body.customer_id}' not found")

    ledger_res = (
        db.table("khata_ledger")
        .select("balance")
        .eq("customer_id", body.customer_id)
        .execute()
    )
    current_balance = float(ledger_res.data[0]["balance"]) if ledger_res.data else 0.0

    if body.action == "payment_received":
        new_balance = current_balance - body.amount
    else:  # credit_given
        new_balance = current_balance + body.amount

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    db.table("khata_ledger").upsert({
        "customer_id": body.customer_id,
        "balance": new_balance,
        "last_payment_date": now,
        "updated_at": now,
    }).execute()

    logger.info(
        f"Khata record added: customer={body.customer_id} action={body.action} "
        f"amount={body.amount} new_balance={new_balance}"
    )
    return {
        "status": "recorded",
        "customer_id": body.customer_id,
        "action": body.action,
        "amount": body.amount,
        "new_balance": new_balance,
    }


@router.post("/broadcast", dependencies=[Depends(get_current_admin)])
async def broadcast(body: BroadcastRequest) -> dict:
    svc = NotificationService()
    result = await svc.send_broadcast(body.message, body.store_ids)
    return result
