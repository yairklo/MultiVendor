from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from fastapi.responses import StreamingResponse
from app.db.session import get_db
from app.deps import get_tenant_admin
from app.models.user import User
from app.schemas.catalog_schemas import (
    ProductCreateRequest, ProductUpdateRequest, ProductResponse,
    ProductVariantSchema, CategoryCreateRequest, CategoryResponse,
    ProductReviewResponse
)
from app.schemas.tenant_schemas import TenantSettingsSchema
from app.services.catalog_service import (
    create_category_service, delete_category_service,
    create_product_service, update_product_service, delete_product_service,
    add_product_variant_service, update_product_variant_service,
    update_review_status_service, export_orders_csv_service
)
from app.services.tenant_service import update_store_settings_service

# For admin orders, we might need to import order service, but we can put it in catalog or tenant service for now or create order_service
from app.services.order_service import update_order_status_service

tenant_admin_router = APIRouter(prefix="/api/v1/admin/store/{tenant_slug}", tags=["Tenant Admin & CMS"])

# CATEGORIES
@tenant_admin_router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    req: CategoryCreateRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await create_category_service(tenant_slug, req, db)

@tenant_admin_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    await delete_category_service(tenant_slug, category_id, db)
    return None

# PRODUCTS
@tenant_admin_router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    req: ProductCreateRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await create_product_service(tenant_slug, req, db)

@tenant_admin_router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    req: ProductUpdateRequest,
    product_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_product_service(tenant_slug, product_id, req, db)

@tenant_admin_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    await delete_product_service(tenant_slug, product_id, db)
    return None

# VARIANTS
@tenant_admin_router.post("/products/{product_id}/variants", response_model=ProductVariantSchema, status_code=status.HTTP_201_CREATED)
async def add_product_variant(
    req: ProductVariantSchema,
    product_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await add_product_variant_service(tenant_slug, product_id, req, db)

@tenant_admin_router.put("/variants/{variant_id}", response_model=ProductVariantSchema)
async def update_product_variant(
    req: ProductVariantSchema,
    variant_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_product_variant_service(tenant_slug, variant_id, req, db)

# STORE SETTINGS
@tenant_admin_router.put("/settings", response_model=TenantSettingsSchema)
async def update_store_settings(
    req: TenantSettingsSchema,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_store_settings_service(tenant_slug, req, db)

# REVIEWS MODERATION
@tenant_admin_router.patch("/reviews/{review_id}/status", response_model=ProductReviewResponse)
async def update_review_status(
    review_id: int = Path(...),
    status: str = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_review_status_service(tenant_slug, review_id, status, db)

# ORDERS STATUS
@tenant_admin_router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int = Path(...),
    status: str = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_order_status_service(tenant_slug, order_id, status, db)

# REPORTS EXPORT
@tenant_admin_router.get("/reports/export")
async def export_reports(
    report_type: str = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    if report_type == "orders":
        return await export_orders_csv_service(tenant_slug, db)
    # can add more later
    pass
