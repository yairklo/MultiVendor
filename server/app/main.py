import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.core.observability import configure_observability
import app.models  # Ensure all models are registered with SQLAlchemy
from app.core.limiter import limiter
from app.db.session import redis_client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal, get_db
from app.services.tasks import cleanup_abandoned_checkouts, cleanup_expired_guest_carts

configure_observability()

logger = logging.getLogger(__name__)
CHECKOUT_CLEANUP_INTERVAL_SECONDS = 60
GUEST_CART_CLEANUP_INTERVAL_SECONDS = 6 * 60 * 60

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
    },
    {
        "name": "Marketplace",
        "description": "Cross-store marketplace: browse products from any opted-in vendor, and check out a multi-vendor cart in one call via order splitting.",
    }
]

from fastapi.middleware.cors import CORSMiddleware

async def _checkout_cleanup_loop():
    # Orders left in "pending_payment" (the customer never clicked Pay, or
    # walked away) are periodically expired and their reserved stock
    # released. In mock mode that's a short (15min) timeout; in stripe mode
    # an order with an open PaymentIntent gets a much longer grace window
    # and is only expired after that PaymentIntent is explicitly canceled
    # first. See app/services/tasks.py.
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await cleanup_abandoned_checkouts(session)
        except Exception:
            logger.exception("checkout cleanup sweep failed")
        await asyncio.sleep(CHECKOUT_CLEANUP_INTERVAL_SECONDS)

async def _guest_cart_cleanup_loop():
    # Guest carts (Cart.user_id IS NULL) are protected by a time-limited
    # capability token (see app/core/cart_token.py); once that token's TTL
    # has passed the cart can never be reached again, so it's safe to purge.
    while True:
        try:
            async with AsyncSessionLocal() as session:
                await cleanup_expired_guest_carts(session)
        except Exception:
            logger.exception("guest cart cleanup sweep failed")
        await asyncio.sleep(GUEST_CART_CLEANUP_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = asyncio.create_task(_checkout_cleanup_loop())
    guest_cart_task = asyncio.create_task(_guest_cart_cleanup_loop())
    yield
    cleanup_task.cancel()
    guest_cart_task.cancel()

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
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        # This middleware is what turns the exception into a clean 500 response,
        # which means it never propagates to Sentry's own ASGI instrumentation --
        # report it explicitly instead. A no-op if SENTRY_DSN isn't set.
        import sentry_sdk
        sentry_sdk.capture_exception()
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred.", "code": "INTERNAL_ERROR"}
        )

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # A CSP isn't set here: this is a JSON API (plus /docs and /uploads), and
    # the frontend -- the thing actually rendering untrusted HTML/JS -- is
    # where a content policy belongs (see frontend/next.config.ts).
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    redis_status = "connected"

    try:
        await db.execute(text("SELECT 1"))
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

if settings.APP_ENV != "production":
    @app.get("/health/error_test")
    async def health_error_test():
        raise Exception("Test error")


from app.routers.auth_router import auth_router
from app.routers.customer_router import customer_router
from app.routers.super_admin_router import super_admin_router
from app.routers.storefront_router import storefront_router
from app.routers.domain_router import domain_router
from app.routers.cart_router import cart_router
from app.routers.tenant_admin_router import tenant_admin_router
from app.routers.ai_router import ai_router
from app.routers.marketplace_router import marketplace_router
from app.routers.payments_router import payments_router

app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(super_admin_router)
app.include_router(storefront_router)
app.include_router(domain_router)
app.include_router(cart_router)
app.include_router(tenant_admin_router)
app.include_router(ai_router)
app.include_router(marketplace_router)
app.include_router(payments_router)
