from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv
import os

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    # Server
    PORT: int = 8000
    DEBUG: bool = True
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # AI / SLM
    AI_MODEL_ENDPOINT: str = "http://localhost:11434/api/generate"
    BHASHINI_API_KEY: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # WhatsApp
    WHATSAPP_VERIFY_TOKEN: str = "digital_store_manager_verify"
    WHATSAPP_ACCESS_TOKEN: str = ""

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
