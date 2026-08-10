from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from fastapi.responses import StreamingResponse
from app.db.session import get_db
from app.deps import get_tenant_admin
from app.models.user import User
from app.models.tenant import Tenant, SubscriptionPlan
from app.schemas.catalog_schemas import (
    ProductCreateRequest, ProductUpdateRequest, ProductResponse,
    ProductVariantSchema, CategoryCreateRequest, CategoryResponse,
    ProductReviewResponse
)
from app.schemas.tenant_schemas import TenantSettingsSchema, TenantUpdateSchema, TenantResponse
from app.services.catalog_service import (
    create_category_service, delete_category_service,
    create_product_service, get_admin_product_service, update_product_service, delete_product_service,
    add_product_variant_service, update_product_variant_service,
    update_review_status_service, export_orders_csv_service
)
from app.services.tenant_service import (
    update_store_settings_service, update_tenant_service, get_tenant_analytics_service,
    upgrade_subscription_service, get_current_subscription_service
)

# For admin orders, we might need to import order service, but we can put it in catalog or tenant service for now or create order_service
from app.services.order_service import update_order_status_service

tenant_admin_router = APIRouter(prefix="/api/v1/admin/store/{tenant_slug}", tags=["Tenant Admin & CMS"])

# CATEGORIES
@tenant_admin_router.post(
    "/categories", 
    response_model=CategoryResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create Category",
    description="Creates a new product category. Enforces Row-Level Security ensuring it's partitioned to the caller's tenant.",
    responses={201: {"description": "Category created successfully."}}
)
async def create_category(
    req: CategoryCreateRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await create_category_service(tenant_slug, req, db)

@tenant_admin_router.get("/categories")
async def get_categories(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    from app.models.catalog import Category
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = await db.execute(select(Category).where(Category.tenant_id == tenant.id))
    return result.scalars().all()

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
@tenant_admin_router.post(
    "/products", 
    response_model=ProductResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create Product",
    description="Creates a new product. **Architectural Note:** Before creation, the system strictly checks the store's `subscription_plan`. If the store has reached its `max_products` quota, the request is rejected with a `403 Forbidden`.",
    responses={
        201: {"description": "Product created successfully."},
        403: {"description": "Subscription limit reached. Cannot create more products."}
    }
)
async def create_product(
    req: ProductCreateRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await create_product_service(tenant_slug, req, db)

@tenant_admin_router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await get_admin_product_service(tenant_slug, product_id, db)

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
@tenant_admin_router.post(
    "/products/{product_id}/variants", 
    response_model=ProductVariantSchema, 
    status_code=status.HTTP_201_CREATED,
    summary="Add Product Variant",
    description="Adds a new variant (e.g., Size, Color) to an existing product.",
    responses={
        201: {"description": "Variant successfully added."},
        404: {"description": "Product not found or access denied due to RLS."}
    }
)
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

# TENANT UPDATE
@tenant_admin_router.put(
    "/domain",
    response_model=TenantResponse,
    summary="Update Custom Domain"
)
async def update_tenant_domain(
    req: TenantUpdateSchema,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_tenant_service(tenant_slug, req, db)

# SUBSCRIPTION
@tenant_admin_router.post(
    "/subscription/upgrade",
    summary="Upgrade Subscription Plan"
)
async def upgrade_subscription(
    target_plan_code: str = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await upgrade_subscription_service(tenant_slug, target_plan_code, db)

@tenant_admin_router.get(
    "/subscription/current",
    summary="Get Current Subscription Plan"
)
async def get_current_subscription(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await get_current_subscription_service(tenant_slug, db)

# STORE SETTINGS
@tenant_admin_router.put(
    "/settings", 
    response_model=TenantSettingsSchema,
    summary="Update Store Settings",
    description="Updates the store's public UI configuration, tax rates, and branding.",
    responses={200: {"description": "Settings successfully updated."}}
)
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
@tenant_admin_router.get(
    "/reports/export",
    summary="Export Reports (CSV)",
    description="Generates a downloadable CSV report for the specified report type (e.g. 'orders').",
    responses={
        200: {"description": "CSV stream starting."}
    }
)
async def export_reports(
    report_type: str = Query(..., description="Type of report to export (e.g., 'orders')"),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    if report_type == "orders":
        return await export_orders_csv_service(tenant_slug, db)
    # can add more later
    pass

# ANALYTICS
@tenant_admin_router.get(
    "/analytics",
    summary="Get Store Analytics"
)
async def get_analytics(
    start_date: str = Query(...),
    end_date: str = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await get_tenant_analytics_service(tenant_slug, start_date, end_date, db)


# ORDERS (Missing backlog endpoints)
@tenant_admin_router.get('/orders')
async def get_tenant_orders(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    from app.models.order import Order
    from sqlalchemy import select
    from fastapi import HTTPException
    
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail='Tenant not found')
        
    result = await db.execute(select(Order).where(Order.tenant_id == tenant.id))
    return result.scalars().all()

@tenant_admin_router.get('/orders/{order_id}')
async def get_tenant_order_details(
    order_id: int,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    from app.models.order import Order
    from sqlalchemy import select
    from fastapi import HTTPException
    
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail='Tenant not found')
        
    result = await db.execute(select(Order).where(Order.tenant_id == tenant.id, Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    return order
