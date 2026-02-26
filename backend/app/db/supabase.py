from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()

def get_supabase_client() -> Client:
    """Returns a Supabase client using the anon key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_supabase_admin_client() -> Client:
    """Returns a Supabase client using the service role key for admin tasks. Fallback to anon key if missing."""
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
    return create_client(settings.SUPABASE_URL, key)
