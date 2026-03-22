import logging
import os
import time
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from configs.config import get_settings
from backend.app.core.logging_config import setup_logging
from backend.app.api.v1 import whatsapp, compliance
from backend.app.api.v1 import admin, inventory, alerts, khata
from backend.app.dashboard.router import router as dashboard_router

setup_logging()

logger = logging.getLogger(__name__)
settings = get_settings()
logger.info("Main module loaded")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ZnShop — Digital Store Manager API",
    version="2.0.0",
    description="AI-powered WhatsApp backend for Indian Kirana stores.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "REQUEST_ERROR | %s %s | %.1fms",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "REQUEST | %s %s | %d | %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(whatsapp.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")  # serves /customers routes
app.include_router(admin.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")  # serves /alerts routes
app.include_router(khata.router, prefix="/api/v1")  # serves /khata routes
app.include_router(dashboard_router)  # HTML dashboard
logger.info("Routes loaded")


@app.on_event("startup")
async def _log_routes() -> None:
    logger.info("Startup begin")
    from fastapi.routing import APIRoute
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    logger.info("=== Registered routes (%d) ===", len(routes))
    for r in sorted(routes, key=lambda x: x.path):
        methods = ",".join(sorted(r.methods or []))
        logger.info("  %-8s %s", methods, r.path)
    supabase_url = ((settings.SUPABASE_URL or "") or (os.getenv("SUPABASE_URL") or "")).strip()
    supabase_key = ((settings.SUPABASE_KEY or "") or (os.getenv("SUPABASE_KEY") or "")).strip()
    service_role_key = ((settings.SUPABASE_SERVICE_ROLE_KEY or "") or (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "")).strip()
    supabase_host = urlparse(supabase_url).netloc if supabase_url else "missing"
    project_ref = supabase_host.split(".")[0] if supabase_host and supabase_host != "missing" else "unknown"
    logger.info(
        "SUPABASE_TARGET | host=%s project_ref=%s key_source=%s",
        supabase_host,
        project_ref,
        "service_role" if service_role_key else ("anon_key" if supabase_key else "missing"),
    )
    logger.info(
        "ENV | SUPABASE_URL=%s SUPABASE_KEY=%s REDIS_URL=%s AI_MODEL_ENDPOINT=%s",
        "set" if supabase_url else "missing",
        "set" if supabase_key else "missing",
        "set" if ((settings.REDIS_URL or "") or (os.getenv("REDIS_URL") or "")).strip() else "missing",
        "set" if (((settings.AI_MODEL_ENDPOINT or "") or (settings.OLLAMA_URL or "") or (os.getenv("AI_MODEL_ENDPOINT") or "") or (os.getenv("OLLAMA_URL") or "")).strip()) else "missing",
    )
    logger.info("Services initialized")


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "service": "ZnShop API", "version": app.version}
