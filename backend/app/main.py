from fastapi import FastAPI, APIRouter
from app.api.v1 import whatsapp, compliance
from app.core.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title="Digital Store Manager API",
    version="1.0.0",
    debug=settings.DEBUG
)

# Root endpoints
@app.get("/health")
async def health(): return {"status": "ok"}

# Register routers
app.include_router(whatsapp.router, prefix="/api/v1/whatsapp", tags=["WhatsApp"])
app.include_router(compliance.router, prefix="/api/v1/customers", tags=["Compliance"])

# To be added: inventory, transactions
