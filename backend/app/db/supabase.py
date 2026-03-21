import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_anon_client: Client | None = None
_admin_client: Client | None = None


def _env_values() -> tuple[str, str, str]:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    service_role_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    print("SUPABASE_URL:", url)
    print("SUPABASE_KEY:", "exists" if key else "missing")
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
        _admin_client = create_client(url, use_key)
    return _admin_client


def get_supabase_client_safe() -> Client | None:
    try:
        return get_supabase_client()
    except Exception as exc:
        print("Supabase init failed:", exc)
        return None


def get_supabase_admin_client_safe() -> Client | None:
    try:
        return get_supabase_admin_client()
    except Exception as exc:
        print("Supabase init failed:", exc)
        return None
