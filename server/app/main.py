import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
import app.models  # Ensure all models are registered with SQLAlchemy
from app.core.limiter import limiter
from app.db.session import redis_client
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.services.tasks import cleanup_abandoned_checkouts

logger = logging.getLogger(__name__)
CHECKOUT_CLEANUP_INTERVAL_SECONDS = 60

openapi_tags = [
    {
        "name": "Authentication & Onboarding",
        "description": "Endpoints for user login, registration, and JWT token issuance.",
    },
    {
        "name": "Public Storefront",
        "description": "Publicly accessible endpoints for storefront UI to fetch tenant configuration and catalogs.",
    },
    {
        "name": "Tenant Admin & CMS",
        "description": "Secured endpoints for store owners to manage products, categories, variants, and reviews. Enforces subscription limits via Row-Level Security.",
    },
    {
        "name": "Cart & Checkout",
        "description": "Shopping cart lifecycle and checkout engine. Uses distributed Redis Locks to prevent overselling.",
    },
    {
        "name": "Customer Portal",
        "description": "Endpoints for authenticated customers to manage their profile and view past orders.",
    },
    {
        "name": "Super Admin",
        "description": "Global administration endpoints to manage system-wide settings and monitor all tenants.",
    }
]

from fastapi.middleware.cors import CORSMiddleware

async def _checkout_cleanup_loop():
    # Dev-only mock payment flow: orders left in "pending_payment" (the
    # customer never clicked Pay, or walked away) are periodically expired
    # and their reserved stock released. See app/services/tasks.py.
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await cleanup_abandoned_checkouts(session)
        except Exception:
            logger.exception("checkout cleanup sweep failed")
        await asyncio.sleep(CHECKOUT_CLEANUP_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(_checkout_cleanup_loop())
    yield
    cleanup_task.cancel()

app = FastAPI(
    title="MultiVendor Hub API",
    description="A fully featured Multi-Tenancy E-Commerce Platform API. Supports Row-Level Security, Redis Distributed Locks, and Subscription enforcement.",
    version="1.0.0",
    docs_url="/docs",
    openapi_tags=openapi_tags,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3005", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "code": "INTERNAL_ERROR"}
        )

@app.get("/health")
async def health_check():
    db_status = "connected"
    redis_status = "connected"
    
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"
        
    status_code = 200 if db_status == "connected" and redis_status == "connected" else 500
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if status_code == 200 else "unhealthy", "database": db_status, "redis": redis_status}
    )

@app.get("/health/error_test")
async def health_error_test():
    raise Exception("Test error")


from app.routers.auth_router import auth_router
from app.routers.customer_router import customer_router
from app.routers.super_admin_router import super_admin_router
from app.routers.storefront_router import storefront_router
from app.routers.cart_router import cart_router
from app.routers.tenant_admin_router import tenant_admin_router
from app.routers.ai_router import ai_router

app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(super_admin_router)
app.include_router(storefront_router)
app.include_router(cart_router)
app.include_router(tenant_admin_router)
app.include_router(ai_router)
