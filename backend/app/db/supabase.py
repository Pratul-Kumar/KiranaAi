from supabase import create_client, Client
from configs.config import get_settings

settings = get_settings()

_anon_client: Client | None = None
_admin_client: Client | None = None


def get_supabase_client() -> Client:
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _anon_client


def get_supabase_admin_client() -> Client:
    global _admin_client
    if _admin_client is None:
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        _admin_client = create_client(settings.SUPABASE_URL, key)
    return _admin_client
