from functools import lru_cache

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    OLLAMA_URL: str = "http://localhost:11434"
    AI_MODEL_ENDPOINT: str | None = None
    AI_MODEL_NAME: str = "mistral"
    BHASHINI_API_KEY: str = ""

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # WhatsApp (Meta Graph API)
    WHATSAPP_VERIFY_TOKEN: str = "znshop_verify"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # Admin / Security
    JWT_SECRET: str = "change-me-in-production"
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    ADMIN_EMAIL: str = "admin@znshop.local"
    ADMIN_PASSWORD: str = "changeme"
    ADMIN_PASSWORD_HASH: str = ""

    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    # Admin Dashboard
    ZNSHOP_API_URL: str = "http://localhost:8000/api/v1"

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def signing_key(self) -> str:
        return self.JWT_SECRET or self.SECRET_KEY or "change-me-in-production"

    @property
    def resolved_ai_model_endpoint(self) -> str:
        return self.AI_MODEL_ENDPOINT or f"{self.OLLAMA_URL.rstrip('/')}/api/generate"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return ["*"]
            if value.startswith("["):
                return value
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
