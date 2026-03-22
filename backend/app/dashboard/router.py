"""
app/dashboard/router.py — HTML Admin Dashboard served at /admin
Session-cookie based auth (separate from JWT REST API).
"""
import logging
import os
import httpx
from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt

from configs.config import get_settings
from backend.app.core.security import create_access_token, verify_password

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])
logger = logging.getLogger(__name__)
settings = get_settings()

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

COOKIE_NAME = "znshop_session"


# session helpers


def _get_session_email(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.signing_key, algorithms=["HS256"])
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

def _require_token(znshop_session: str | None = Cookie(default=None)) -> str:
    if not znshop_session or not _get_session_email(znshop_session):
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return znshop_session

def _ctx(request: Request, active: str, email: str, **extra) -> dict:
    """Build base template context."""
    return {"request": request, "active": active, "session_email": email, **extra}


def _admin_api_base(request: Request) -> str:
    configured = (os.getenv("ZNSHOP_API_URL") or "").strip()
    if configured:
        return configured.rstrip("/")
    return f"{request.base_url.scheme}://{request.base_url.netloc}/api/v1"


async def _safe_api_get(request: Request, token: str, path: str, key: str, default: list | dict) -> list | dict:
    try:
        payload = await api_get(request, path, token)
        value = payload.get(key, default)
        if value is None:
            logger.warning("Dashboard API '%s' returned null for key '%s'", path, key)
            return default
        size = len(value) if isinstance(value, list) else 1
        logger.info("Dashboard API '%s' success (items=%s)", path, size)
        return value
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        body = exc.response.text[:500] if exc.response is not None else ""
        logger.error("Dashboard API '%s' HTTP error %s: %s", path, status, body)
    except Exception as exc:
        logger.exception("Dashboard API '%s' request failed: %s", path, exc)
    return default

# API helpers
async def api_get(request: Request, path: str, token: str) -> dict:
    url = f"{_admin_api_base(request)}/admin/{path}"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            cookies={"access_token": token, COOKIE_NAME: token},
        )
        resp.raise_for_status()
        return resp.json()

async def api_post(request: Request, path: str, token: str, json_data: dict) -> dict:
    url = f"{_admin_api_base(request)}/admin/{path}"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.post(
            url,
            json=json_data,
            headers={"Authorization": f"Bearer {token}"},
            cookies={"access_token": token, COOKIE_NAME: token},
        )
        resp.raise_for_status()
        return resp.json()

async def api_delete(request: Request, path: str, token: str) -> dict:
    url = f"{_admin_api_base(request)}/admin/{path}"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.delete(
            url,
            headers={"Authorization": f"Bearer {token}"},
            cookies={"access_token": token, COOKIE_NAME: token},
        )
        resp.raise_for_status()
        return resp.json()

# auth

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
        secure=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        "access_token", token,
        httponly=True, samesite="lax",
        secure=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    logger.info("Dashboard login: %s", email)
    return response


@router.get("/logout", include_in_schema=False)
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# dashboard home

@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_home(request: Request, email: str = Depends(_require_session), token: str = Depends(_require_token)):
    logger.info("Dashboard route entered for %s", email)
    try:
        stores = await _safe_api_get(request, token, "stores", "stores", [])
        vendors = await _safe_api_get(request, token, "vendors", "vendors", [])
        alerts = await _safe_api_get(request, token, "alerts", "alerts", [])
        
        stats = {
            "stores": len(stores),
            "vendors": len(vendors),
            "alerts": len(alerts),
            "customers": 0
        }
        
        return templates.TemplateResponse("home.html", _ctx(request, "home", email,
            stats=stats, recent_stores=stores[:5], recent_alerts=alerts[:5]))
    except Exception as exc:
        logger.exception("Dashboard render failure: %s", exc)
        return templates.TemplateResponse("home.html", _ctx(
            request,
            "home",
            email,
            stats={"stores": 0, "vendors": 0, "alerts": 0, "customers": 0},
            recent_stores=[],
            recent_alerts=[],
            flash={"type": "error", "msg": "Dashboard loaded with limited data"},
        ))

# stores

@router.get("/stores", response_class=HTMLResponse, include_in_schema=False)
async def stores_page(request: Request, email: str = Depends(_require_session), token: str = Depends(_require_token), flash: str | None = None):
    stores = await _safe_api_get(request, token, "stores", "stores", [])
    return templates.TemplateResponse(
        "stores.html",
        _ctx(request, "stores", email, stores=stores, flash=None),
    )


@router.post("/stores/create", include_in_schema=False)
async def store_create(
    request: Request,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token),
    name: str = Form(...),
    owner_name: str = Form(...),
    contact_phone: str = Form(...),
    address: str = Form(""),
):
    try:
        await api_post(request, "stores", token, {
            "name": name, "owner_name": owner_name,
            "contact_phone": contact_phone, "address": address,
        })
    except httpx.HTTPStatusError as e:
        logger.error("Store create API error: %s", e)
        if e.response.status_code == 409:
            logger.warning("Duplicate store phone")
    except Exception as exc:
        logger.error("Store create error: %s", exc)
    return RedirectResponse("/admin/stores", status_code=302)

@router.post("/stores/{store_id}/delete", include_in_schema=False)
async def store_delete(
    request: Request,
    store_id: str,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token)
):
    try:
        await api_delete(request, f"stores/{store_id}", token)
    except httpx.HTTPStatusError as e:
        logger.error("Store delete API error: %s", e)
    return RedirectResponse("/admin/stores", status_code=302)

# vendors

@router.get("/vendors", response_class=HTMLResponse, include_in_schema=False)
async def vendors_page(request: Request, email: str = Depends(_require_session), token: str = Depends(_require_token)):
    vendors = await _safe_api_get(request, token, "vendors", "vendors", [])
    stores = await _safe_api_get(request, token, "stores", "stores", [])
    return templates.TemplateResponse(
        "vendors.html",
        _ctx(request, "vendors", email, vendors=vendors, stores=stores, flash=None),
    )


@router.post("/vendors/create", include_in_schema=False)
async def vendor_create(
    request: Request,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token),
    name: str = Form(...),
    phone: str = Form(...),
    category: str = Form("other"),
):
    try:
        await api_post(request, "vendors", token, {"name": name, "phone": phone, "category": category})
    except Exception as exc:
        logger.error("Vendor create error: %s", exc)
    return RedirectResponse("/admin/vendors", status_code=302)


@router.post("/vendors/{vendor_id}/delete", include_in_schema=False)
async def vendor_delete(
    request: Request,
    vendor_id: str,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token)
):
    try:
        await api_delete(request, f"vendors/{vendor_id}", token)
    except Exception as exc:
        logger.error("Vendor delete error: %s", exc)
    return RedirectResponse("/admin/vendors", status_code=302)

@router.post("/vendors/assign", include_in_schema=False)
async def vendor_assign(
    request: Request,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token),
    store_id: str = Form(...),
    vendor_id: str = Form(...),
):
    try:
        await api_post(request, "assign-vendor", token, {"store_id": store_id, "vendor_id": vendor_id})
    except Exception as exc:
        logger.error("Assign vendor error: %s", exc)
    return RedirectResponse("/admin/vendors", status_code=302)


# inventory

@router.get("/inventory", response_class=HTMLResponse, include_in_schema=False)
async def inventory_page(
    request: Request,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token),
    store_id: str | None = None,
):
    stores = await _safe_api_get(request, token, "stores", "stores", [])
    inventory = []
    if store_id:
        inventory = await _safe_api_get(request, token, f"inventory/{store_id}", "inventory", [])
    return templates.TemplateResponse("inventory.html", _ctx(request, "inventory", email,
        stores=stores, inventory=inventory, selected_store=store_id))


# khata

@router.get("/khata", response_class=HTMLResponse, include_in_schema=False)
async def khata_page(
    request: Request,
    email: str = Depends(_require_session),
    token: str = Depends(_require_token),
    store_id: str | None = None,
):
    stores_data = {"stores": []}
    try:
        stores_data = await api_get(request, "stores", token)
    except Exception as exc:
        logger.error("Khata stores query failed: %s", exc)
    records = []
    if store_id:
        try:
            khata_data = await api_get(request, f"khata/{store_id}", token)
            records = khata_data.get("khata", [])
        except Exception as e:
            logger.error(f"Khata API error: {e}")
    return templates.TemplateResponse("khata.html", _ctx(request, "khata", email,
        stores=stores_data.get("stores", []), records=records, selected_store=store_id))
