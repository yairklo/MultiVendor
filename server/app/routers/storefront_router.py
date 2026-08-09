from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.schemas.tenant_schemas import TenantSettingsSchema
from app.schemas.catalog_schemas import PaginatedProductResponse, ProductResponse
from app.services.catalog_service import get_store_config_service, list_public_products_service, get_public_product_service

storefront_router = APIRouter(prefix="/api/v1/store", tags=["Public Storefront"])

@storefront_router.get("/{tenant_slug}/config", response_model=TenantSettingsSchema)
async def get_store_config(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch public configuration (colors, logo, currency) for a storefront."""
    return await get_store_config_service(tenant_slug, db)

@storefront_router.get("/{tenant_slug}/products", response_model=PaginatedProductResponse)
async def list_products(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List active products for a specific storefront with pagination and search."""
    return await list_public_products_service(tenant_slug, page, page_size, q, category_id, db)

@storefront_router.get("/{tenant_slug}/products/{product_slug}", response_model=ProductResponse)
async def get_product(
    tenant_slug: str = Path(..., title="Tenant Slug"),
    product_slug: str = Path(..., title="Product Slug"),
    db: AsyncSession = Depends(get_db)
):
    """Get full details of a single product including variants and images."""
    return await get_public_product_service(tenant_slug, product_slug, db)
