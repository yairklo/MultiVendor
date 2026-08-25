from fastapi import APIRouter, Depends, status, Query, Path, HTTPException, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Literal
from fastapi.responses import StreamingResponse
from app.db.session import get_db
from app.deps import get_tenant_admin, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant, SubscriptionPlan
from app.services.storage_service import save_image
from app.schemas.upload_schemas import ImageUploadResponse
from app.services.import_service import build_import_template, parse_products_excel, commit_products_import
from app.schemas.import_schemas import ImportPreviewResponse, ImportCommitRequest, ImportSummaryResponse
from app.schemas.catalog_schemas import (
    ProductCreateRequest, ProductUpdateRequest, ProductResponse,
    ProductVariantSchema, CategoryCreateRequest, CategoryResponse,
    ProductReviewResponse
)
from app.schemas.order_schemas import (
    OrderResponse, CouponCreateRequest, CouponResponse,
    OrderStatusUpdateResponse
)
from app.schemas.shipping_schemas import (
    ShippingProviderCode, TenantShippingConfigCreate, TenantShippingConfigResponse,
    FulfillOrderResponse
)
from app.schemas.auth_schemas import CustomerSummaryResponse
from app.schemas.tenant_schemas import (
    TenantSettingsSchema, TenantUpdateSchema, TenantResponse, TenantSettingsUpdateSchema,
    SubscriptionPlanInfo, TenantAnalyticsResponse, TenantMarketplaceVisibilityUpdateSchema
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
    upgrade_subscription_service, get_current_subscription_service, get_top_selling_products_service,
    update_marketplace_visibility_service
)
from app.services.order_service import (
    update_order_status_service, list_tenant_orders_service, get_tenant_order_service,
    list_tenant_customers_service
)
from app.services.coupon_service import (
    list_tenant_coupons_service, create_tenant_coupon_service, delete_tenant_coupon_service
)
from app.services.shipping_service import (
    list_tenant_shipping_configs_service, upsert_tenant_shipping_config_service,
    delete_tenant_shipping_config_service, fulfill_order_service
)

tenant_admin_router = APIRouter(
    prefix="/api/v1/admin/store/{tenant_slug}",
    tags=["Tenant Admin & CMS"],
    dependencies=[Depends(get_current_tenant)],
)

# UPLOADS
@tenant_admin_router.post(
    "/uploads/image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a Product Image",
    description="Uploads an image file and returns its URL. Not product-scoped -- upload first, then use the returned URL wherever an image_url field is expected (e.g. creating a product).",
    responses={
        201: {"description": "Image uploaded successfully."},
        400: {"description": "File is not a valid image, unsupported format, or exceeds the 5MB limit."}
    }
)
async def upload_product_image(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(get_tenant_admin),
):
    url = await save_image(file, tenant.id)
    return ImageUploadResponse(url=url)

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

# PRODUCTS / INVENTORY IMPORT
@tenant_admin_router.get(
    "/products/import/template",
    summary="Download Product Import Template",
    description="Downloads a blank .xlsx with the expected column headers for the products/inventory import.",
    responses={200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}}}}
)
async def download_import_template():
    content = build_import_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=product_import_template.xlsx"},
    )

@tenant_admin_router.post(
    "/products/import/preview",
    response_model=ImportPreviewResponse,
    summary="Preview a Product/Inventory Import",
    description="Parses an uploaded .xlsx and validates each row without writing anything to the database.",
)
async def preview_products_import(
    file: UploadFile = File(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
):
    raw = await file.read()
    return parse_products_excel(raw)

@tenant_admin_router.post(
    "/products/import/commit",
    response_model=ImportSummaryResponse,
    summary="Commit a Product/Inventory Import",
    description="Creates new products or updates stock/price on existing ones (matched by SKU) from previously-previewed rows.",
)
async def commit_products_import_endpoint(
    req: ImportCommitRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await commit_products_import(tenant_slug, [r.model_dump() for r in req.rows], db)

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

# MARKETPLACE
@tenant_admin_router.put(
    "/marketplace-visibility",
    response_model=TenantResponse,
    summary="Set Store-Wide Marketplace Visibility",
    description="Toggles whether every active product of this store is eligible for the cross-store marketplace listing. A product can still opt in individually (see PUT .../products/{id} `show_in_marketplace`) even if this is off.",
)
async def update_marketplace_visibility(
    req: TenantMarketplaceVisibilityUpdateSchema,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await update_marketplace_visibility_service(tenant_slug, req, db)

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
    req: TenantSettingsUpdateSchema,
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

# SHIPPING PROVIDER CONFIG
@tenant_admin_router.get("/shipping-config", response_model=list[TenantShippingConfigResponse])
async def list_shipping_config(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await list_tenant_shipping_configs_service(tenant_slug, db)

@tenant_admin_router.put("/shipping-config", response_model=TenantShippingConfigResponse)
async def upsert_shipping_config(
    req: TenantShippingConfigCreate,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await upsert_tenant_shipping_config_service(tenant_slug, req, db)

@tenant_admin_router.delete("/shipping-config/{provider}")
async def delete_shipping_config(
    provider: ShippingProviderCode,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await delete_tenant_shipping_config_service(tenant_slug, provider, db)

# ORDER FULFILLMENT
@tenant_admin_router.post("/orders/{order_id}/fulfill", response_model=FulfillOrderResponse)
async def fulfill_order(
    order_id: int = Path(...),
    provider: Optional[ShippingProviderCode] = Query(None, description="Override the store's default courier for this order."),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    return await fulfill_order_service(tenant_slug, order_id, db, provider_override=provider)

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

from pydantic import BaseModel

class StripeConnectResponse(BaseModel):
    url: str

class StripeConnectStatusResponse(BaseModel):
    is_connected: bool
    account_id: Optional[str]

@tenant_admin_router.post(
    "/stripe/connect",
    response_model=StripeConnectResponse,
    summary="Create Stripe Connect Onboarding Link"
)
async def create_stripe_connect(
    return_url: str = Query(...),
    refresh_url: str = Query(...),
    tenant_slug: str = Path(...),
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db)
):
    from app.services.payments import get_payment_provider
    try:
        provider = get_payment_provider()
    except ValueError:
        raise HTTPException(status_code=400, detail="Stripe Connect not supported by current provider")
        
    if not hasattr(provider, 'create_connect_account'):
        raise HTTPException(status_code=400, detail="Stripe Connect not supported by current provider")
    
    if not tenant.stripe_account_id:
        tenant.stripe_account_id = await provider.create_connect_account()
        await db.commit()
    
    url = await provider.create_account_link(tenant.stripe_account_id, refresh_url, return_url)
    return StripeConnectResponse(url=url)

@tenant_admin_router.get(
    "/stripe/connect/status",
    response_model=StripeConnectStatusResponse,
    summary="Check Stripe Connect Status"
)
async def get_stripe_connect_status(
    tenant_slug: str = Path(...),
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(get_tenant_admin),
):
    return StripeConnectStatusResponse(
        is_connected=bool(tenant.stripe_account_id),
        account_id=tenant.stripe_account_id
    )
