import logging
import os

from dotenv import load_dotenv
from supabase import create_client, Client
from configs.config import get_settings

load_dotenv()

logger = logging.getLogger(__name__)
settings = get_settings()

_anon_client: Client | None = None
_admin_client: Client | None = None


def _mask_key(key: str) -> str:
    if not key:
        return "missing"
    if len(key) <= 8:
        return "present(len<=8)"
    return f"present({key[:4]}...{key[-4:]},len={len(key)})"


def _env_values() -> tuple[str, str, str]:
    url = ((settings.SUPABASE_URL or "") or (os.getenv("SUPABASE_URL") or "")).strip()
    key = ((settings.SUPABASE_KEY or "") or (os.getenv("SUPABASE_KEY") or "")).strip()
    service_role_key = ((settings.SUPABASE_SERVICE_ROLE_KEY or "") or (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "")).strip()
    logger.info(
        "Supabase env check | url=%s anon_key=%s service_role=%s",
        url or "missing",
        _mask_key(key),
        _mask_key(service_role_key),
    )
    return url, key, service_role_key


def get_supabase_client() -> Client:
    global _anon_client
    if _anon_client is None:
        url, key, _ = _env_values()
        if not url or not key:
            raise ValueError("Missing Supabase env variables: SUPABASE_URL/SUPABASE_KEY")
        _anon_client = create_client(url, key)
    return _anon_client


def get_supabase_admin_client() -> Client:
    global _admin_client
    if _admin_client is None:
        url, key, service_role_key = _env_values()
        use_key = service_role_key or key
        if not url or not use_key:
            raise ValueError("Missing Supabase env variables: SUPABASE_URL/SUPABASE_KEY")
        logger.info(
            "Initializing Supabase admin client | url=%s key_source=%s",
            url,
            "service_role" if service_role_key else "anon_key",
        )
        _admin_client = create_client(url, use_key)
    return _admin_client


def get_supabase_client_safe() -> Client | None:
    try:
        return get_supabase_client()
    except Exception as exc:
        logger.exception("Supabase anon client init failed: %s", exc)
        return None


def get_supabase_admin_client_safe() -> Client | None:
    try:
        return get_supabase_admin_client()
    except Exception as exc:
        logger.exception("Supabase admin client init failed: %s", exc)
        return None
