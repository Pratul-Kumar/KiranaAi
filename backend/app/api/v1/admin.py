import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from configs.config import get_settings
from backend.app.core.security import create_access_token, get_current_admin, verify_password
from backend.app.db.supabase import get_supabase_admin_client
from backend.app.models.schemas import (
    AdminLoginRequest,
    AssignVendorRequest,
    BroadcastRequest,
    KhataAddRequest,
    StoreCreate,
    TokenResponse,
    VendorCreate,
)
from backend.app.services.notification_service import NotificationService
from postgrest.exceptions import APIError

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)
settings = get_settings()


def _is_valid_admin_password(password: str) -> bool:
    hashed_password = getattr(settings, "ADMIN_PASSWORD_HASH", "")
    if isinstance(hashed_password, str) and hashed_password.strip():
        return verify_password(password, hashed_password)
    return password == settings.ADMIN_PASSWORD


# ──────────────────────────────────────────────────────────────────────────────
# Public routes (no auth required)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("", summary="Admin API root")
async def admin_root() -> dict:
    """Lists all available admin endpoints."""
    return {
        "service": "ZnShop Admin API",
        "version": "2.0.0",
        "auth": {
            "swagger": "POST /api/v1/admin/token  (form: username + password)",
            "curl":    "POST /api/v1/admin/login   (JSON: email + password)",
        },
        "endpoints": {
            "stores_list":   "GET  /api/v1/admin/stores",
            "store_create":  "POST /api/v1/admin/stores",
            "vendors_list":  "GET  /api/v1/admin/vendors",
            "vendor_create": "POST /api/v1/admin/vendors",
            "assign_vendor": "POST /api/v1/admin/assign-vendor",
            "inventory":     "GET  /api/v1/admin/inventory/{store_id}",
            "khata":         "GET  /api/v1/admin/khata/{store_id}",
            "khata_add":     "POST /api/v1/admin/khata/add",
            "alerts":        "GET  /api/v1/admin/alerts",
            "broadcast":     "POST /api/v1/admin/broadcast",
        },
        "docs": "/docs",
    }


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 token endpoint (used by Swagger Authorize button)",
    include_in_schema=True,
)
async def admin_token(form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """
    OAuth2 standard form-data login. Swagger's Authorize button calls this endpoint.
    Fields: username (= email), password.
    """
    if form.username != settings.ADMIN_EMAIL or not _is_valid_admin_password(form.password):
        logger.warning("Failed Swagger login attempt for: %s", form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": form.username})
    logger.info("Admin token issued via /token for: %s", form.username)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="JSON login (curl / API clients)",
)
async def admin_login(body: AdminLoginRequest) -> TokenResponse:
    """JSON body login for curl and API clients."""
    if body.email != settings.ADMIN_EMAIL or not _is_valid_admin_password(body.password):
        logger.warning("Failed login attempt for: %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token({"sub": body.email})
    logger.info("Admin token issued via /login for: %s", body.email)
    return TokenResponse(access_token=token)


# ──────────────────────────────────────────────────────────────────────────────
# Protected routes (JWT required)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/stores", dependencies=[Depends(get_current_admin)])
async def create_store(body: StoreCreate) -> dict:
    db = get_supabase_admin_client()
    try:
        res = db.table("stores").insert(body.model_dump(exclude_none=True)).execute()
        return {"status": "created", "store": res.data[0] if res.data else {}}
    except APIError as e:
        err_dict = e.json()
        if err_dict.get("code") == "23505":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store with this phone number already exists.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err_dict))


@router.get("/stores", dependencies=[Depends(get_current_admin)])
async def list_stores() -> dict:
    db = get_supabase_admin_client()
    res = db.table("stores").select("*").order("created_at", desc=True).execute()
    return {"stores": res.data}


@router.post("/vendors", dependencies=[Depends(get_current_admin)])
async def create_vendor(body: VendorCreate) -> dict:
    db = get_supabase_admin_client()
    try:
        res = db.table("vendors").insert(body.model_dump()).execute()
        return {"status": "created", "vendor": res.data[0] if res.data else {}}
    except APIError as e:
        err_dict = e.json()
        if err_dict.get("code") == "23505":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vendor with this phone number already exists.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err_dict))


@router.delete("/stores/{store_id}", dependencies=[Depends(get_current_admin)])
async def delete_store(store_id: str) -> dict:
    db = get_supabase_admin_client()
    db.table("stores").delete().eq("id", store_id).execute()
    return {"status": "deleted", "store_id": store_id}


@router.get("/vendors", dependencies=[Depends(get_current_admin)])
async def list_vendors() -> dict:
    db = get_supabase_admin_client()
    res = db.table("vendors").select("*").order("name").execute()
    return {"vendors": res.data}


@router.delete("/vendors/{vendor_id}", dependencies=[Depends(get_current_admin)])
async def delete_vendor(vendor_id: str) -> dict:
    db = get_supabase_admin_client()
    db.table("vendors").delete().eq("id", vendor_id).execute()
    return {"status": "deleted", "vendor_id": vendor_id}


@router.post("/assign-vendor", dependencies=[Depends(get_current_admin)])
async def assign_vendor(body: AssignVendorRequest) -> dict:
    db = get_supabase_admin_client()
    db.table("store_vendors").upsert({
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

@router.get("/inventory", dependencies=[Depends(get_current_admin)])
async def get_all_inventory() -> dict:
    db = get_supabase_admin_client()
    res = (
        db.table("inventory")
        .select("*, skus(name, category_path, store_id)")
        .execute()
    )
    return {"inventory": res.data}


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

@router.get("/khata", dependencies=[Depends(get_current_admin)])
async def get_all_khata() -> dict:
    db = get_supabase_admin_client()
    res = (
        db.table("khata_ledger")
        .select("*, customers(name, phone, store_id)")
        .execute()
    )
    return {"khata": res.data}


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

    cust_res = db.table("customers").select("id").eq("id", body.customer_id).execute()
    if not cust_res.data:
        raise HTTPException(status_code=404, detail=f"Customer '{body.customer_id}' not found")

    ledger_res = db.table("khata_ledger").select("balance").eq("customer_id", body.customer_id).execute()
    current_balance = float(ledger_res.data[0]["balance"]) if ledger_res.data else 0.0

    new_balance = current_balance - body.amount if body.action == "payment_received" else current_balance + body.amount

    now = datetime.now(timezone.utc).isoformat()
    db.table("khata_ledger").upsert({
        "customer_id": body.customer_id,
        "balance": new_balance,
        "last_payment_date": now,
        "updated_at": now,
    }).execute()

    logger.info(
        "Khata record: customer=%s action=%s amount=%s new_balance=%s",
        body.customer_id, body.action, body.amount, new_balance,
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
    return await svc.send_broadcast(body.message, body.store_ids)
