from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Literal
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
from app.schemas.order_schemas import (
    OrderResponse, CouponCreateRequest, CouponResponse,
    OrderStatusUpdateResponse
)
from app.schemas.auth_schemas import CustomerSummaryResponse
from app.schemas.tenant_schemas import (
    TenantSettingsSchema, TenantUpdateSchema, TenantResponse,
    SubscriptionPlanInfo, TenantAnalyticsResponse
)
from app.schemas.ai_schemas import TopSellingProduct
from app.schemas.common_schemas import PlanCode
from app.services.catalog_service import (
    create_category_service, delete_category_service,
    create_product_service, get_admin_product_service, update_product_service, delete_product_service,
    add_product_variant_service, update_product_variant_service,
    update_review_status_service, export_orders_csv_service, list_tenant_reviews_service
)
from app.services.tenant_service import (
    update_store_settings_service, update_tenant_service, get_tenant_analytics_service,
    upgrade_subscription_service, get_current_subscription_service, get_top_selling_products_service
)
from app.services.order_service import (
    update_order_status_service, list_tenant_orders_service, get_tenant_order_service,
    list_tenant_customers_service
)
from app.services.coupon_service import (
    list_tenant_coupons_service, create_tenant_coupon_service, delete_tenant_coupon_service
)

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

@tenant_admin_router.get("/categories", response_model=list[CategoryResponse])
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
    response_model=SubscriptionPlanInfo,
    summary="Upgrade Subscription Plan"
)
async def upgrade_subscription(
    target_plan_code: PlanCode = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await upgrade_subscription_service(tenant_slug, target_plan_code.value, db)

@tenant_admin_router.get(
    "/subscription/current",
    response_model=SubscriptionPlanInfo,
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
@tenant_admin_router.get("/reviews", response_model=list[ProductReviewResponse])
async def get_tenant_reviews(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await list_tenant_reviews_service(tenant_slug, db)

@tenant_admin_router.patch("/reviews/{review_id}/status", response_model=ProductReviewResponse)
async def update_review_status(
    review_id: int = Path(...),
    status: Literal["approved", "rejected", "pending"] = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_review_status_service(tenant_slug, review_id, status, db)

# ORDERS STATUS
@tenant_admin_router.patch("/orders/{order_id}/status", response_model=OrderStatusUpdateResponse)
async def update_order_status(
    order_id: int = Path(...),
    status: Literal["processing", "completed", "cancelled"] = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_order_status_service(tenant_slug, order_id, status, db)

# REPORTS EXPORT
@tenant_admin_router.get(
    "/reports/export",
    summary="Export Reports (CSV)",
    description="Generates a downloadable CSV report for the specified report type (currently only 'orders').",
    responses={
        200: {
            "description": "CSV stream starting.",
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}
        }
    }
)
async def export_reports(
    report_type: Literal["orders"] = Query(..., description="Type of report to export."),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await export_orders_csv_service(tenant_slug, db)

# ANALYTICS
@tenant_admin_router.get(
    "/analytics",
    response_model=TenantAnalyticsResponse,
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

@tenant_admin_router.get(
    "/analytics/top-products",
    response_model=list[TopSellingProduct],
    summary="Get Top Selling Products"
)
async def get_top_selling_products(
    start_date: str = Query(...),
    end_date: str = Query(...),
    limit: int = Query(5),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await get_top_selling_products_service(tenant_slug, start_date, end_date, db, limit)


# ORDERS
@tenant_admin_router.get('/orders', response_model=list[OrderResponse])
async def get_tenant_orders(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await list_tenant_orders_service(tenant_slug, db)

@tenant_admin_router.get('/orders/{order_id}', response_model=OrderResponse)
async def get_tenant_order_details(
    order_id: int,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await get_tenant_order_service(tenant_slug, order_id, db)

# CUSTOMERS (CRM)
@tenant_admin_router.get(
    '/customers',
    response_model=list[CustomerSummaryResponse],
    summary="List Store Customers",
    description="Lists customers who have an account with this store, with order count, total spend (from paid orders), and last order date."
)
async def get_tenant_customers(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await list_tenant_customers_service(tenant_slug, db)

# COUPONS
@tenant_admin_router.get('/coupons', response_model=list[CouponResponse])
async def get_tenant_coupons(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await list_tenant_coupons_service(tenant_slug, db)

@tenant_admin_router.post('/coupons', response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_coupon(
    req: CouponCreateRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await create_tenant_coupon_service(tenant_slug, req, db)

@tenant_admin_router.delete('/coupons/{coupon_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_coupon(
    coupon_id: int = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    await delete_tenant_coupon_service(tenant_slug, coupon_id, db)
    return None
