from fastapi import FastAPI
from app.core.config import settings
import app.models  # Ensure all models are registered with SQLAlchemy

app = FastAPI(title="MultiVendor Hub", version="1.0.0", description="MultiVendor E-Commerce Platform API")

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
