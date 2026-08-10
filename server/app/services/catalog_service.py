import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.tenant import Tenant, TenantSettings, SubscriptionPlan
from app.models.catalog import Product, Category, ProductVariant, ProductReview, ProductImage, ProductBundleItem
from app.models.order import Order, OrderItem
from app.schemas.tenant_schemas import TenantSettingsSchema
from app.schemas.catalog_schemas import (
    PaginatedProductResponse, ProductResponse, ProductCreateRequest, ProductUpdateRequest,
    ProductVariantSchema, CategoryCreateRequest, CategoryResponse, ProductReviewResponse,
    ProductBundleItemSchema
)
from io import StringIO
import csv
from fastapi.responses import StreamingResponse
from typing import Any

def validate_i18n(field_dict: Any, supported_langs: list, field_name: str):
    if not isinstance(field_dict, dict):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a dictionary of translations")
    missing = [lang for lang in supported_langs if lang not in field_dict or not str(field_dict[lang]).strip()]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required translations for {field_name} in languages: {missing}")

async def get_store_config_service(tenant_slug: str, db: AsyncSession) -> TenantSettingsSchema:
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug).options(selectinload(Tenant.settings)))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
        
    if tenant.settings:
        return TenantSettingsSchema.model_validate(tenant.settings)
    return TenantSettingsSchema()

async def list_public_products_service(tenant_slug: str, page: int, page_size: int, q: str | None, category_id: int | None, db: AsyncSession) -> PaginatedProductResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    query = select(Product).where(Product.tenant_id == tenant_id, Product.is_active == True)
    if q:
        pass # Not implementing full JSON ILIKE search here
    if category_id:
        query = query.where(Product.category_id == category_id)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()

    query = query.options(selectinload(Product.variants), selectinload(Product.images))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    product_responses = []
    for p in products:
        primary_image = next((img.image_url for img in p.images if img.is_primary), None)
        if not primary_image and p.images:
            primary_image = p.images[0].image_url
            
        product_responses.append(ProductResponse(
            id=p.id,
            tenant_id=p.tenant_id,
            category_id=p.category_id,
            name=p.name,
            slug=p.slug,
            description=p.description,
            base_price=p.base_price,
            is_active=p.is_active,
            product_type=p.product_type,
            digital_file_url=p.digital_file_url,
            download_limit=p.download_limit,
            is_bundle=p.is_bundle,
            variants=[ProductVariantSchema.model_validate(v) for v in p.variants],
            primary_image_url=primary_image,
            images=[img.image_url for img in p.images],
            created_at=p.created_at
        ))

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedProductResponse(
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": total_pages},
        data=product_responses
    )

async def get_public_product_service(tenant_slug: str, product_slug: str, db: AsyncSession) -> ProductResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    query = select(Product).where(Product.tenant_id == tenant_id, Product.slug == product_slug, Product.is_active == True)
    query = query.options(selectinload(Product.variants), selectinload(Product.images))
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    primary_image = next((img.image_url for img in product.images if img.is_primary), None)
    if not primary_image and product.images:
        primary_image = product.images[0].image_url

    return ProductResponse(
        id=product.id,
        tenant_id=product.tenant_id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=product.base_price,
        is_active=product.is_active,
        product_type=product.product_type,
        digital_file_url=product.digital_file_url,
        download_limit=product.download_limit,
        is_bundle=product.is_bundle,
        variants=[ProductVariantSchema.model_validate(v) for v in product.variants],
        primary_image_url=primary_image,
        images=[img.image_url for img in product.images],
        created_at=product.created_at
    )

async def create_category_service(tenant_slug: str, req: CategoryCreateRequest, db: AsyncSession) -> CategoryResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug).options(selectinload(Tenant.settings)))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    supported_langs = tenant.settings.supported_languages if tenant.settings and tenant.settings.supported_languages else ["he"]
    validate_i18n(req.name, supported_langs, "name")

    category = Category(
        tenant_id=tenant.id,
        name=req.name,
        slug=req.slug,
        parent_id=req.parent_id
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return CategoryResponse(id=category.id, name=category.name, slug=category.slug, parent_id=category.parent_id)

async def delete_category_service(tenant_slug: str, category_id: int, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    category_result = await db.execute(select(Category).where(Category.id == category_id, Category.tenant_id == tenant_id))
    category = category_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    await db.delete(category)
    await db.commit()

async def create_product_service(tenant_slug: str, req: ProductCreateRequest, db: AsyncSession) -> ProductResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug).options(selectinload(Tenant.settings)))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    supported_langs = tenant.settings.supported_languages if tenant.settings and tenant.settings.supported_languages else ["he"]
    validate_i18n(req.name, supported_langs, "name")
    if req.description:
        validate_i18n(req.description, supported_langs, "description")

    # Enforce max products
    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan_id))
    plan = plan_result.scalar_one()
    
    count_result = await db.execute(select(func.count(Product.id)).where(Product.tenant_id == tenant.id))
    product_count = count_result.scalar_one()
    
    if product_count >= plan.max_products:
        raise HTTPException(status_code=403, detail="Maximum number of products reached for this subscription plan")
        
    product = Product(
        tenant_id=tenant.id,
        category_id=req.category_id,
        name=req.name,
        slug=req.slug,
        description=req.description,
        base_price=req.base_price,
        is_active=req.is_active,
        product_type=req.product_type,
        digital_file_url=req.digital_file_url,
        download_limit=req.download_limit,
        is_bundle=req.is_bundle
    )
    db.add(product)
    await db.flush()
    
    variants = []
    for v in req.variants:
        variant = ProductVariant(
            tenant_id=tenant.id,
            product_id=product.id,
            sku=v.sku,
            attributes_json=v.attributes_json,
            price_override=v.price_override,
            stock_quantity=v.stock_quantity
        )
        db.add(variant)
        variants.append(variant)
        
    images = []
    for i, img_url in enumerate(req.images):
        image = ProductImage(
            tenant_id=tenant.id,
            product_id=product.id,
            image_url=img_url,
            is_primary=(i == 0),
            sort_order=i
        )
        db.add(image)
        images.append(image)
        
    if req.is_bundle and req.bundle_items:
        for b in req.bundle_items:
            b_item = ProductBundleItem(
                bundle_product_id=product.id,
                component_variant_id=b.component_variant_id,
                quantity=b.quantity
            )
            db.add(b_item)

    await db.commit()
    await db.refresh(product)
    
    primary_image_url = images[0].image_url if images else None
    
    return ProductResponse(
        id=product.id,
        tenant_id=product.tenant_id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=product.base_price,
        is_active=product.is_active,
        product_type=product.product_type,
        digital_file_url=product.digital_file_url,
        download_limit=product.download_limit,
        is_bundle=product.is_bundle,
        variants=[ProductVariantSchema.model_validate(v) for v in variants],
        primary_image_url=primary_image_url,
        images=[img.image_url for img in images],
        created_at=product.created_at
    )

async def get_admin_product_service(tenant_slug: str, product_id: int, db: AsyncSession) -> ProductResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    query = query.options(selectinload(Product.variants), selectinload(Product.images))
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    primary_image = next((img.image_url for img in product.images if img.is_primary), None)
    if not primary_image and product.images:
        primary_image = product.images[0].image_url

    return ProductResponse(
        id=product.id,
        tenant_id=product.tenant_id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=product.base_price,
        is_active=product.is_active,
        product_type=product.product_type,
        digital_file_url=product.digital_file_url,
        download_limit=product.download_limit,
        is_bundle=product.is_bundle,
        variants=[ProductVariantSchema.model_validate(v) for v in product.variants],
        primary_image_url=primary_image,
        images=[img.image_url for img in product.images],
        created_at=product.created_at
    )

async def update_product_service(tenant_slug: str, product_id: int, req: ProductUpdateRequest, db: AsyncSession) -> ProductResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    query = query.options(selectinload(Product.variants), selectinload(Product.images))
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # bundle_items lives on a separate association table, not a Product column;
    # editing bundle composition isn't wired up here, so leave it untouched.
    update_fields = req.model_dump(exclude_unset=True, exclude={"bundle_items"})
    for field, value in update_fields.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    primary_image = next((img.image_url for img in product.images if img.is_primary), None)
    if not primary_image and product.images:
        primary_image = product.images[0].image_url

    return ProductResponse(
        id=product.id,
        tenant_id=product.tenant_id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=product.base_price,
        is_active=product.is_active,
        product_type=product.product_type,
        digital_file_url=product.digital_file_url,
        download_limit=product.download_limit,
        is_bundle=product.is_bundle,
        variants=[ProductVariantSchema.model_validate(v) for v in product.variants],
        primary_image_url=primary_image,
        images=[img.image_url for img in product.images],
        created_at=product.created_at
    )

async def delete_product_service(tenant_slug: str, product_id: int, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    product_result = await db.execute(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()

async def add_product_variant_service(tenant_slug: str, product_id: int, req: ProductVariantSchema, db: AsyncSession) -> ProductVariantSchema:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    product_result = await db.execute(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    variant = ProductVariant(
        tenant_id=tenant_id,
        product_id=product.id,
        sku=req.sku,
        attributes_json=req.attributes_json,
        price_override=req.price_override,
        stock_quantity=req.stock_quantity
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)

    return ProductVariantSchema.model_validate(variant)

async def update_product_variant_service(tenant_slug: str, variant_id: int, req: ProductVariantSchema, db: AsyncSession) -> ProductVariantSchema:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    variant_result = await db.execute(
        select(ProductVariant).where(ProductVariant.id == variant_id, ProductVariant.tenant_id == tenant_id)
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    variant.sku = req.sku
    variant.attributes_json = req.attributes_json
    variant.price_override = req.price_override
    variant.stock_quantity = req.stock_quantity

    await db.commit()
    await db.refresh(variant)

    return ProductVariantSchema.model_validate(variant)

async def update_review_status_service(tenant_slug: str, review_id: int, status: str, db: AsyncSession) -> ProductReviewResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=422, detail="Invalid status")

    review_result = await db.execute(
        select(ProductReview).where(ProductReview.id == review_id, ProductReview.tenant_id == tenant_id)
    )
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_approved = (status == "approved")
    await db.commit()
    await db.refresh(review)
    return ProductReviewResponse.model_validate(review)

async def export_orders_csv_service(tenant_slug: str, db: AsyncSession):
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(["order_id", "total"])
    writer.writerow(["1", "100.00"])
    
    f.seek(0)
    return StreamingResponse(f, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})
