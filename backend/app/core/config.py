from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # AI / SLM
    AI_MODEL_ENDPOINT: str = "http://localhost:11434/api/generate"
    AI_MODEL_NAME: str = "mistral"
    BHASHINI_API_KEY: str = ""

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # WhatsApp (Meta Graph API)
    WHATSAPP_VERIFY_TOKEN: str = "znshop_verify"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # Admin / Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_EMAIL: str = "admin@znshop.local"
    ADMIN_PASSWORD: str = "changeme"

    # Admin Dashboard
    ZNSHOP_API_URL: str = "http://localhost:8000/api/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
