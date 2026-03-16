import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.api.v1 import whatsapp, compliance
from app.api.v1 import admin, inventory, alerts, khata
from app.dashboard.router import router as dashboard_router

setup_logging()

logger = logging.getLogger(__name__)
settings = get_settings()

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
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
app.include_router(compliance.router, prefix="/api/v1")   # router owns /customers prefix
app.include_router(admin.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(alerts.router,     prefix="/api/v1")   # router prefix: /alerts
app.include_router(khata.router,      prefix="/api/v1")   # router prefix: /khata
app.include_router(dashboard_router)                       # HTML dashboard at /admin


@app.on_event("startup")
async def _log_routes() -> None:
    from fastapi.routing import APIRoute
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    logger.info("=== Registered routes (%d) ===", len(routes))
    for r in sorted(routes, key=lambda x: x.path):
        methods = ",".join(sorted(r.methods or []))
        logger.info("  %-8s %s", methods, r.path)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    from fastapi.routing import APIRoute
    route_count = sum(1 for r in app.routes if isinstance(r, APIRoute))
    return {"status": "ok", "service": "ZnShop API", "version": app.version, "routes": route_count}
