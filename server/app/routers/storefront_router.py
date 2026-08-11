from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.deps import get_tenant_customer
from app.models.user import User
from app.schemas.tenant_schemas import TenantSettingsSchema
from app.schemas.catalog_schemas import (
    PaginatedProductResponse, ProductResponse, ProductReviewResponse, ProductReviewCreateRequest,
    CategoryResponse
)
from app.services.catalog_service import (
    get_store_config_service, list_public_products_service, get_public_product_service,
    list_product_reviews_service, create_product_review_service, list_public_categories_service
)
from app.schemas.ai_schemas import StorePageSchema
from app.services.store_page_service import get_published_page_schema_service

storefront_router = APIRouter(prefix="/api/v1/store", tags=["Public Storefront"])

@storefront_router.get(
    "/{tenant_slug}/config", 
    response_model=TenantSettingsSchema,
    summary="Get Public Storefront Configuration",
    description="Retrieves the public settings for a store (e.g., branding colors, logo URL, currency, tax rates). Used by the frontend to dynamically style the shop.",
    responses={
        200: {"description": "Store configuration successfully retrieved."},
        404: {"description": "Tenant store not found."}
    }
)
async def get_store_config(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    db: AsyncSession = Depends(get_db)
):
    return await get_store_config_service(tenant_slug, db)

@storefront_router.get(
    "/{tenant_slug}/categories",
    response_model=list[CategoryResponse],
    summary="List Storefront Categories",
    description="Lists categories for a storefront's category filter/navigation.",
    responses={
        200: {"description": "Categories successfully retrieved."},
        404: {"description": "Tenant store not found."}
    }
)
async def get_public_categories(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    db: AsyncSession = Depends(get_db)
):
    return await list_public_categories_service(tenant_slug, db)

@storefront_router.get(
    "/{tenant_slug}/products",
    response_model=PaginatedProductResponse,
    summary="List Public Storefront Products",
    description="Lists active products for a specific storefront. Includes pagination, optional search query matching, and category filtering.",
    responses={
        200: {"description": "Successfully retrieved a paginated list of active products."},
        404: {"description": "Tenant store not found."}
    }
)
async def list_products(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    return await list_public_products_service(tenant_slug, page, page_size, q, category_id, db)

@storefront_router.get(
    "/{tenant_slug}/products/{product_slug}", 
    response_model=ProductResponse,
    summary="Get Product Details",
    description="Fetches full details of a single active product, including all associated product variants, current stock levels, and product images.",
    responses={
        200: {"description": "Product details successfully retrieved."},
        404: {"description": "Product or Tenant store not found."}
    }
)
async def get_product(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    product_slug: str = Path(..., title="Product Slug"),
    db: AsyncSession = Depends(get_db)
):
    return await get_public_product_service(tenant_slug, product_slug, db)

@storefront_router.get(
    "/{tenant_slug}/products/{product_slug}/reviews",
    response_model=list[ProductReviewResponse],
    summary="List Approved Product Reviews",
    description="Lists approved reviews for a product, with resolved customer names.",
    responses={
        200: {"description": "Reviews successfully retrieved."},
        404: {"description": "Product or Tenant store not found."}
    }
)
async def get_product_reviews(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    product_slug: str = Path(..., title="Product Slug"),
    db: AsyncSession = Depends(get_db)
):
    return await list_product_reviews_service(tenant_slug, product_slug, db)

@storefront_router.get(
    "/{tenant_slug}/pages/{page_key}",
    response_model=StorePageSchema,
    summary="Get a Storefront Page's Section Layout",
    description=(
        "Fetches the AI/CMS-managed JSON section layout for a public static page (e.g. 'home'), so the "
        "storefront can render it dynamically. Only ever serves page_type='static_page' — 'template' is an "
        "internal editing concept and is never exposed publicly. Only ever serves the store owner's last "
        "*published* version — draft edits from the AI/admin preview are invisible here until explicitly "
        "published, even if they were made moments ago."
    ),
    responses={
        200: {"description": "Page layout successfully retrieved."},
        404: {"description": "Page not found, or has no published version yet."}
    }
)
async def get_storefront_page(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    page_key: str = Path(..., title="Page Key"),
    db: AsyncSession = Depends(get_db)
):
    return await get_published_page_schema_service(tenant_slug, page_key, "static_page", db)

@storefront_router.post(
    "/{tenant_slug}/reviews",
    response_model=ProductReviewResponse,
    status_code=201,
    summary="Submit a Product Review",
    description="Authenticated customers can leave one review per product. Reviews are auto-approved unless the store has review moderation enabled, and are flagged as verified-buyer if the customer has a paid order containing the product.",
    responses={
        201: {"description": "Review submitted."},
        400: {"description": "Already reviewed this product."},
        404: {"description": "Product or Tenant store not found."}
    }
)
async def submit_product_review(
    req: ProductReviewCreateRequest,
    tenant_slug: str = Path(..., title="Tenant Slug"),
    user: User = Depends(get_tenant_customer),
    db: AsyncSession = Depends(get_db)
):
    return await create_product_review_service(tenant_slug, user.id, req, db)
