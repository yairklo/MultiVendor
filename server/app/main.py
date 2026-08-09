from fastapi import FastAPI
from app.core.config import settings
import app.models  # Ensure all models are registered with SQLAlchemy

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

app = FastAPI(
    title="MultiVendor Hub API",
    description="A fully featured Multi-Tenancy E-Commerce Platform API. Supports Row-Level Security, Redis Distributed Locks, and Subscription enforcement.",
    version="1.0.0",
    docs_url="/docs",
    openapi_tags=openapi_tags
)
@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.APP_ENV}

from app.routers.auth_router import auth_router
from app.routers.customer_router import customer_router
from app.routers.super_admin_router import super_admin_router
from app.routers.storefront_router import storefront_router
from app.routers.cart_router import cart_router
from app.routers.tenant_admin_router import tenant_admin_router

app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(super_admin_router)
app.include_router(storefront_router)
app.include_router(cart_router)
app.include_router(tenant_admin_router)
