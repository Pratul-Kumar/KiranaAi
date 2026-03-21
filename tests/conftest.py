"""
conftest.py — makes `app` importable when pytest runs from the project root.
Injects dummy env vars so Pydantic Settings validation passes without a real .env.
"""
import os
import sys

# let tests import backend.app.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# set required env vars before imports
os.environ.setdefault("SUPABASE_URL",              "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY",              "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("SECRET_KEY",                "test-secret-key")
os.environ.setdefault("ADMIN_EMAIL",               "admin@znshop.local")
os.environ.setdefault("ADMIN_PASSWORD",            "testpass")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN",     "znshop_verify")
os.environ.setdefault("REDIS_URL",                 "redis://localhost:6379/0")
