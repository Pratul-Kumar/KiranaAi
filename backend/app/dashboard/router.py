"""
app/dashboard/router.py — HTML Admin Dashboard served at /admin
Session-cookie based auth (separate from JWT REST API).
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt

from configs.config import get_settings
from src.core.security import create_access_token, verify_password
from src.db.supabase import get_supabase_admin_client, get_supabase_client

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])
logger = logging.getLogger(__name__)
settings = get_settings()

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

COOKIE_NAME = "znshop_session"


# ──────────────────────────────────────────────────────────────────────────────
# Session helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_session_email(znshop_session: str | None) -> str | None:
    if not znshop_session:
        return None
    try:
        payload = jwt.decode(znshop_session, settings.signing_key, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None


def _is_valid_admin_password(password: str) -> bool:
    hashed_password = getattr(settings, "ADMIN_PASSWORD_HASH", "")
    if isinstance(hashed_password, str) and hashed_password.strip():
        return verify_password(password, hashed_password)
    return password == settings.ADMIN_PASSWORD


def _require_session(znshop_session: str | None = Cookie(default=None)) -> str:
    email = _get_session_email(znshop_session)
    if not email:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return email


def _ctx(request: Request, active: str, email: str, **extra) -> dict:
    """Build base template context."""
    return {"request": request, "active": active, "session_email": email, **extra}


# ──────────────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, znshop_session: str | None = Cookie(default=None)):
    if _get_session_email(znshop_session):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "session_email": None, "error": None})


@router.post("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if email != settings.ADMIN_EMAIL or not _is_valid_admin_password(password):
        logger.warning("Dashboard login failed for: %s", email)
        return templates.TemplateResponse("login.html", {
            "request": request, "session_email": None,
            "error": "Invalid email or password",
        })

    token = create_access_token({"sub": email})
    response = RedirectResponse("/admin", status_code=302)
    response.set_cookie(
        COOKIE_NAME, token,
        httponly=True, samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    logger.info("Dashboard login: %s", email)
    return response


@router.get("/logout", include_in_schema=False)
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Home
# ──────────────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_home(request: Request, email: str = Depends(_require_session)):
    db = get_supabase_admin_client()
    stats = {
        "stores":    len(db.table("stores").select("id").execute().data),
        "vendors":   len(db.table("vendors").select("id").execute().data),
        "customers": len(db.table("customers").select("id").execute().data),
        "alerts":    len(db.table("demand_signals").select("id").execute().data),
    }
    recent_stores = db.table("stores").select("name,owner_name,contact_phone").order("created_at", desc=True).limit(5).execute().data
    recent_alerts = db.table("demand_signals").select("sku_id,demand_score,created_at").order("created_at", desc=True).limit(5).execute().data
    return templates.TemplateResponse("home.html", _ctx(request, "home", email,
        stats=stats, recent_stores=recent_stores, recent_alerts=recent_alerts))


# ──────────────────────────────────────────────────────────────────────────────
# Stores
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/stores", response_class=HTMLResponse, include_in_schema=False)
async def stores_page(request: Request, email: str = Depends(_require_session), flash: str | None = None):
    db = get_supabase_admin_client()
    stores = db.table("stores").select("*").order("created_at", desc=True).execute().data
    return templates.TemplateResponse("stores.html", _ctx(request, "stores", email, stores=stores, flash=None))


@router.post("/stores/create", include_in_schema=False)
async def store_create(
    email: str = Depends(_require_session),
    name: str = Form(...),
    owner_name: str = Form(...),
    contact_phone: str = Form(...),
    address: str = Form(""),
):
    db = get_supabase_admin_client()
    try:
        db.table("stores").insert({
            "name": name, "owner_name": owner_name,
            "contact_phone": contact_phone, "address": address,
        }).execute()
    except Exception as exc:
        logger.error("Store create error: %s", exc)
    return RedirectResponse("/admin/stores", status_code=302)


@router.post("/stores/{store_id}/delete", include_in_schema=False)
async def store_delete(store_id: str, email: str = Depends(_require_session)):
    db = get_supabase_admin_client()
    db.table("stores").delete().eq("id", store_id).execute()
    return RedirectResponse("/admin/stores", status_code=302)


# ──────────────────────────────────────────────────────────────────────────────
# Vendors
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/vendors", response_class=HTMLResponse, include_in_schema=False)
async def vendors_page(request: Request, email: str = Depends(_require_session)):
    db = get_supabase_admin_client()
    vendors = db.table("vendors").select("*").order("name").execute().data
    stores  = db.table("stores").select("id,name").order("name").execute().data
    return templates.TemplateResponse("vendors.html", _ctx(request, "vendors", email,
        vendors=vendors, stores=stores, flash=None))


@router.post("/vendors/create", include_in_schema=False)
async def vendor_create(
    email: str = Depends(_require_session),
    name: str = Form(...),
    phone: str = Form(...),
    category: str = Form("other"),
):
    db = get_supabase_admin_client()
    try:
        db.table("vendors").insert({"name": name, "phone": phone, "category": category}).execute()
    except Exception as exc:
        logger.error("Vendor create error: %s", exc)
    return RedirectResponse("/admin/vendors", status_code=302)


@router.post("/vendors/{vendor_id}/delete", include_in_schema=False)
async def vendor_delete(vendor_id: str, email: str = Depends(_require_session)):
    db = get_supabase_admin_client()
    db.table("vendors").delete().eq("id", vendor_id).execute()
    return RedirectResponse("/admin/vendors", status_code=302)


@router.post("/vendors/assign", include_in_schema=False)
async def vendor_assign(
    email: str = Depends(_require_session),
    store_id: str = Form(...),
    vendor_id: str = Form(...),
):
    db = get_supabase_admin_client()
    try:
        db.table("store_vendors").upsert({"store_id": store_id, "vendor_id": vendor_id}).execute()
    except Exception as exc:
        logger.error("Assign vendor error: %s", exc)
    return RedirectResponse("/admin/vendors", status_code=302)


# ──────────────────────────────────────────────────────────────────────────────
# Inventory
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/inventory", response_class=HTMLResponse, include_in_schema=False)
async def inventory_page(
    request: Request,
    email: str = Depends(_require_session),
    store_id: str | None = None,
):
    db = get_supabase_admin_client()
    stores = db.table("stores").select("id,name").order("name").execute().data
    inventory = []
    if store_id:
        inventory = (
            db.table("inventory")
            .select("*, skus(name, category_path, store_id)")
            .eq("skus.store_id", store_id)
            .execute().data
        )
    return templates.TemplateResponse("inventory.html", _ctx(request, "inventory", email,
        stores=stores, inventory=inventory, selected_store=store_id))


# ──────────────────────────────────────────────────────────────────────────────
# Khata
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/khata", response_class=HTMLResponse, include_in_schema=False)
async def khata_page(
    request: Request,
    email: str = Depends(_require_session),
    store_id: str | None = None,
):
    db = get_supabase_admin_client()
    stores = db.table("stores").select("id,name").order("name").execute().data
    records = []
    if store_id:
        records = (
            db.table("khata_ledger")
            .select("*, customers(name, phone, store_id)")
            .eq("customers.store_id", store_id)
            .order("updated_at", desc=True)
            .execute().data
        )
    return templates.TemplateResponse("khata.html", _ctx(request, "khata", email,
        stores=stores, records=records, selected_store=store_id))
