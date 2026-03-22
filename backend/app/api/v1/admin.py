import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from configs.config import get_settings
from backend.app.core.security import create_access_token, get_current_admin, verify_password
from backend.app.db.supabase import get_supabase_admin_client, get_supabase_admin_key_source
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


def _set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def get_current_user(request: Request, admin_payload: dict = Depends(get_current_admin)) -> dict:
    cookie_present = bool(request.cookies.get("access_token") or request.cookies.get("znshop_session"))
    bearer_present = bool(request.headers.get("authorization"))
    logger.info(
        "Admin request auth status | bearer=%s cookie=%s user=%s",
        bearer_present,
        cookie_present,
        admin_payload.get("sub"),
    )
    return admin_payload


def _is_valid_admin_password(password: str) -> bool:
    hashed_password = getattr(settings, "ADMIN_PASSWORD_HASH", "")
    if isinstance(hashed_password, str) and hashed_password.strip():
        return verify_password(password, hashed_password)
    return password == settings.ADMIN_PASSWORD


# public routes

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
async def admin_token(response: Response, form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
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
    _set_access_cookie(response, token)
    logger.info("Admin token issued via /token for: %s", form.username)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="JSON login (curl / API clients)",
)
async def admin_login(body: AdminLoginRequest, response: Response) -> TokenResponse:
    """JSON body login for curl and API clients."""
    if body.email != settings.ADMIN_EMAIL or not _is_valid_admin_password(body.password):
        logger.warning("Failed login attempt for: %s", body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token({"sub": body.email})
    _set_access_cookie(response, token)
    logger.info("Admin token issued via /login for: %s", body.email)
    return TokenResponse(access_token=token)


# protected routes

@router.post("/stores")
async def create_store(request: Request, body: StoreCreate, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Create store request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        payload = body.model_dump(exclude_none=True)
        logger.info("Create store payload | phone=%s name=%s", payload.get("contact_phone"), payload.get("name"))
        res = db.table("stores").insert(body.model_dump(exclude_none=True)).execute()
        created = res.data[0] if res.data else {}
        logger.info("Create store success | created_id=%s", created.get("id"))
        return {"status": "created", "store": created}
    except APIError as e:
        err_dict = e.json()
        logger.error("Create store API error: %s", err_dict)
        if err_dict.get("code") == "23505":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store with this phone number already exists.")
        if err_dict.get("code") == "42P01":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stores table missing. Run schema.sql on the configured Supabase project.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err_dict))
    except Exception as exc:
        logger.exception("Create store unexpected error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Create store failed: {exc}")


@router.get("/stores")
async def list_stores(request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Stores API request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        res = db.table("stores").select("*").order("created_at", desc=True).execute()
        stores = res.data or []
        logger.info("Stores API Supabase response | rows=%d", len(stores))
        return {"stores": stores}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        code = err.get("code") if isinstance(err, dict) else None
        if code == "42P01":
            logger.error("Stores table missing in Supabase (code=42P01). Run schema.sql migration.")
        else:
            logger.error("Stores Supabase API error: %s", err or str(exc))
        return {"stores": []}
    except Exception as exc:
        logger.exception("Stores error: %s", exc)
        return {"stores": []}


@router.post("/vendors")
async def create_vendor(request: Request, body: VendorCreate, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Create vendor request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        payload = body.model_dump()
        logger.info("Create vendor payload | phone=%s name=%s", payload.get("phone"), payload.get("name"))
        res = db.table("vendors").insert(body.model_dump()).execute()
        created = res.data[0] if res.data else {}
        logger.info("Create vendor success | created_id=%s", created.get("id"))
        return {"status": "created", "vendor": created}
    except APIError as e:
        err_dict = e.json()
        logger.error("Create vendor API error: %s", err_dict)
        if err_dict.get("code") == "23505":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vendor with this phone number already exists.")
        if err_dict.get("code") == "42P01":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vendors table missing. Run schema.sql on the configured Supabase project.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err_dict))
    except Exception as exc:
        logger.exception("Create vendor unexpected error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Create vendor failed: {exc}")


def _table_debug(db, table_name: str) -> dict:
    try:
        probe = db.table(table_name).select("id", count="exact").limit(1).execute()
        count = probe.count if getattr(probe, "count", None) is not None else len(probe.data or [])
        return {
            "table": table_name,
            "exists": True,
            "row_count": count,
            "sample_present": bool(probe.data),
        }
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        code = err.get("code") if isinstance(err, dict) else None
        return {
            "table": table_name,
            "exists": code != "42P01",
            "row_count": 0,
            "error": err or str(exc),
        }
    except Exception as exc:
        return {
            "table": table_name,
            "exists": False,
            "row_count": 0,
            "error": str(exc),
        }


@router.get("/debug/db")
async def debug_db_status(request: Request, user: dict = Depends(get_current_user)) -> dict:
    url = (settings.SUPABASE_URL or "").strip()
    key = (settings.SUPABASE_KEY or "").strip()
    service_role_key = (settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()
    logger.info(
        "DB debug requested | user=%s url_present=%s key_present=%s service_role_present=%s",
        user.get("sub"),
        bool(url),
        bool(key),
        bool(service_role_key),
    )
    try:
        db = get_supabase_admin_client()
        stores = _table_debug(db, "stores")
        vendors = _table_debug(db, "vendors")
        return {
            "supabase": {
                "url": url,
                "using_service_role": get_supabase_admin_key_source() == "service_role",
                "effective_key_source": get_supabase_admin_key_source() or "unknown",
                "anon_key_present": bool(key),
                "service_role_key_present": bool(service_role_key),
            },
            "tables": {
                "stores": stores,
                "vendors": vendors,
            },
            "schema_hint": "Run backend/data/schema.sql in Supabase SQL editor if tables are missing.",
        }
    except Exception as exc:
        logger.exception("DB debug failed: %s", exc)
        return {
            "supabase": {
                "url": url,
                "using_service_role": get_supabase_admin_key_source() == "service_role",
                "effective_key_source": get_supabase_admin_key_source() or "unknown",
                "anon_key_present": bool(key),
                "service_role_key_present": bool(service_role_key),
            },
            "error": str(exc),
            "schema_hint": "Check SUPABASE_URL/SUPABASE_KEY in Railway and rerun backend/data/schema.sql.",
        }


@router.delete("/stores/{store_id}")
async def delete_store(store_id: str, request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Delete store request received | path=%s store_id=%s user=%s", request.url.path, store_id, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        existing = db.table("stores").select("id").eq("id", store_id).limit(1).execute()
        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        db.table("stores").delete().eq("id", store_id).execute()
        logger.info("Delete store success | store_id=%s", store_id)
        return {"status": "deleted", "store_id": store_id}
    except HTTPException:
        raise
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Delete store API error: %s", err or str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delete store failed")
    except Exception as exc:
        logger.exception("Delete store unexpected error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Delete store failed: {exc}")


@router.get("/vendors")
async def list_vendors(request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Vendors API request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        res = db.table("vendors").select("*").order("name").execute()
        vendors = res.data or []
        logger.info("Vendors API Supabase response | rows=%d", len(vendors))
        return {"vendors": vendors}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        code = err.get("code") if isinstance(err, dict) else None
        if code == "42P01":
            logger.error("Vendors table missing in Supabase (code=42P01). Run schema.sql migration.")
        else:
            logger.error("Vendors Supabase API error: %s", err or str(exc))
        return {"vendors": []}
    except Exception as exc:
        logger.exception("Vendors error: %s", exc)
        return {"vendors": []}


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str, request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Delete vendor request received | path=%s vendor_id=%s user=%s", request.url.path, vendor_id, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        existing = db.table("vendors").select("id").eq("id", vendor_id).limit(1).execute()
        if not existing.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
        db.table("vendors").delete().eq("id", vendor_id).execute()
        logger.info("Delete vendor success | vendor_id=%s", vendor_id)
        return {"status": "deleted", "vendor_id": vendor_id}
    except HTTPException:
        raise
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Delete vendor API error: %s", err or str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Delete vendor failed")
    except Exception as exc:
        logger.exception("Delete vendor unexpected error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Delete vendor failed: {exc}")


@router.post("/assign-vendor")
async def assign_vendor(request: Request, body: AssignVendorRequest, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Assign vendor request received | path=%s store_id=%s vendor_id=%s user=%s", request.url.path, body.store_id, body.vendor_id, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        db.table("store_vendors").upsert({
            "store_id": body.store_id,
            "vendor_id": body.vendor_id,
        }).execute()
        return {"status": "assigned"}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Assign vendor API error: %s", err or str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Assign vendor failed")
    except Exception as exc:
        logger.exception("Assign vendor unexpected error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Assign vendor failed: {exc}")


@router.get("/inventory/{store_id}")
async def get_store_inventory(store_id: str, request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info(
        "Inventory API request received | path=%s store_id=%s user=%s",
        request.url.path,
        store_id,
        user.get("sub"),
    )
    try:
        db = get_supabase_admin_client()
        res = (
            db.table("inventory")
            .select("*, skus(name, category_path)")
            .eq("skus.store_id", store_id)
            .execute()
        )
        inventory = res.data or []
        logger.info("Inventory API Supabase response | rows=%d", len(inventory))
        return {"store_id": store_id, "inventory": inventory}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Inventory Supabase API error: %s", err or str(exc))
        return {"store_id": store_id, "inventory": []}
    except Exception as exc:
        logger.exception("Inventory error: %s", exc)
        return {"store_id": store_id, "inventory": []}

@router.get("/inventory")
async def get_all_inventory(request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("All inventory API request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        res = (
            db.table("inventory")
            .select("*, skus(name, category_path, store_id)")
            .execute()
        )
        inventory = res.data or []
        logger.info("All inventory API Supabase response | rows=%d", len(inventory))
        return {"inventory": inventory}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("All inventory API error: %s", err or str(exc))
        return {"inventory": []}
    except Exception as exc:
        logger.exception("All inventory unexpected error: %s", exc)
        return {"inventory": []}


@router.get("/khata/{store_id}")
async def get_khata(store_id: str, request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Khata API request received | path=%s store_id=%s user=%s", request.url.path, store_id, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        res = (
            db.table("khata_ledger")
            .select("*, customers(name, phone)")
            .eq("customers.store_id", store_id)
            .execute()
        )
        return {"store_id": store_id, "khata": res.data or []}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Khata API error: %s", err or str(exc))
        return {"store_id": store_id, "khata": []}
    except Exception as exc:
        logger.exception("Khata unexpected error: %s", exc)
        return {"store_id": store_id, "khata": []}

@router.get("/khata")
async def get_all_khata(request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("All khata API request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        res = (
            db.table("khata_ledger")
            .select("*, customers(name, phone, store_id)")
            .execute()
        )
        return {"khata": res.data or []}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("All khata API error: %s", err or str(exc))
        return {"khata": []}
    except Exception as exc:
        logger.exception("All khata unexpected error: %s", exc)
        return {"khata": []}


@router.get("/alerts")
async def get_alerts(request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Alerts API request received | path=%s user=%s", request.url.path, user.get("sub"))
    try:
        db = get_supabase_admin_client()
        res = (
            db.table("demand_signals")
            .select("*")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return {"alerts": res.data or []}
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Alerts API error: %s", err or str(exc))
        return {"alerts": []}
    except Exception as exc:
        logger.exception("Alerts unexpected error: %s", exc)
        return {"alerts": []}


@router.post("/khata/add")
async def add_khata_record(request: Request, body: KhataAddRequest, user: dict = Depends(get_current_user)) -> dict:
    """Add a khata (ledger) record — credit given or payment received."""
    logger.info("Khata add request received | path=%s customer_id=%s user=%s", request.url.path, body.customer_id, user.get("sub"))
    try:
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
    except HTTPException:
        raise
    except APIError as exc:
        err = exc.json() if hasattr(exc, "json") else {}
        logger.error("Khata add API error: %s", err or str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Khata record failed")
    except Exception as exc:
        logger.exception("Khata add unexpected error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Khata record failed: {exc}")


@router.post("/broadcast")
async def broadcast(body: BroadcastRequest, request: Request, user: dict = Depends(get_current_user)) -> dict:
    logger.info("Broadcast request received | path=%s user=%s", request.url.path, user.get("sub"))
    svc = NotificationService()
    try:
        return await svc.send_broadcast(body.message, body.store_ids)
    except Exception as exc:
        logger.exception("Broadcast failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Broadcast failed")
