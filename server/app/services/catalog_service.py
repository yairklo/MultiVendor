import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.tenant import Tenant, TenantSettings, SubscriptionPlan
from app.models.catalog import Product, Category, ProductVariant, ProductReview, ProductImage, ProductBundleItem
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.tenant_schemas import TenantSettingsSchema
from app.schemas.catalog_schemas import (
    PaginatedProductResponse, ProductResponse, ProductCreateRequest, ProductUpdateRequest,
    ProductVariantSchema, CategoryCreateRequest, CategoryResponse, ProductReviewResponse,
    ProductBundleItemSchema, ProductReviewCreateRequest
)
from app.schemas.ai_schemas import InventoryHealthItem, InventoryHealthResponse

# Matches frontend/src/lib/stock.ts's LOW_STOCK_THRESHOLD — per-product configurable
# thresholds don't exist in the schema, so this is a fixed, shared definition of "low".
LOW_STOCK_THRESHOLD = 5
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

def _escape_like(value: str) -> str:
    """Escapes LIKE wildcards so a search for e.g. "50% off" or "a_b" matches
    literally instead of '%'/'_' being treated as SQL wildcards."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

async def _fetch_review_stats(product_ids: list[int], db: AsyncSession) -> dict[int, tuple[float, int]]:
    if not product_ids:
        return {}
    result = await db.execute(
        select(
            ProductReview.product_id,
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .where(ProductReview.product_id.in_(product_ids), ProductReview.is_approved == True)
        .group_by(ProductReview.product_id)
    )
    return {product_id: (float(avg_rating), count) for product_id, avg_rating, count in result.all()}

def _build_product_response(p: "Product", review_stats: dict[int, tuple[float, int]]) -> ProductResponse:
    primary_image = next((img.image_url for img in p.images if img.is_primary), None)
    if not primary_image and p.images:
        primary_image = p.images[0].image_url

    avg_rating, review_count = review_stats.get(p.id, (None, 0))

    return ProductResponse(
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
        average_rating=round(avg_rating, 1) if avg_rating is not None else None,
        review_count=review_count,
        created_at=p.created_at
    )

async def list_public_products_service(tenant_slug: str, page: int, page_size: int, q: str | None, category_id: int | None, db: AsyncSession) -> PaginatedProductResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    conditions = [Product.tenant_id == tenant_id, Product.is_active == True]
    if category_id:
        conditions.append(Product.category_id == category_id)
    if q:
        # name/description are i18n JSON blobs ({"en": "...", "he": "..."}) —
        # casting to text and matching against the whole blob searches every
        # language's value in one LIKE, the same "any translation matches"
        # semantics the old Python-side search had, but evaluated in the DB.
        pattern = f"%{_escape_like(q.strip().lower())}%"
        conditions.append(or_(
            func.lower(cast(Product.name, String)).like(pattern, escape="\\"),
            func.lower(cast(Product.description, String)).like(pattern, escape="\\"),
        ))

    count_result = await db.execute(select(func.count()).select_from(Product).where(*conditions))
    total = count_result.scalar_one()

    query = (
        select(Product)
        .where(*conditions)
        .options(selectinload(Product.variants), selectinload(Product.images))
        .order_by(Product.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    review_stats = await _fetch_review_stats([p.id for p in products], db)
    product_responses = [_build_product_response(p, review_stats) for p in products]

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

    review_stats = await _fetch_review_stats([product.id], db)
    return _build_product_response(product, review_stats)

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

async def list_public_categories_service(tenant_slug: str, db: AsyncSession) -> list[CategoryResponse]:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(select(Category).where(Category.tenant_id == tenant_id).order_by(Category.id))
    return [
        CategoryResponse(id=c.id, name=c.name, slug=c.slug, parent_id=c.parent_id)
        for c in result.scalars().all()
    ]

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

async def get_variant_service(tenant_slug: str, variant_id: int, db: AsyncSession) -> ProductVariantSchema:
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

async def list_tenant_reviews_service(tenant_slug: str, db: AsyncSession) -> list[ProductReviewResponse]:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(ProductReview, Product, User)
        .join(Product, Product.id == ProductReview.product_id)
        .join(User, User.id == ProductReview.user_id)
        .where(ProductReview.tenant_id == tenant_id)
        .order_by(ProductReview.created_at.desc())
    )

    def resolve_name(name):
        if isinstance(name, dict):
            return name.get('en') or next(iter(name.values()), '')
        return str(name)

    return [
        ProductReviewResponse(
            id=review.id,
            product_id=review.product_id,
            product_name=resolve_name(product.name),
            user_id=review.user_id,
            customer_name=customer.full_name,
            rating=review.rating,
            comment=review.comment,
            is_approved=review.is_approved,
            is_verified_buyer=review.is_verified_buyer,
            created_at=review.created_at,
        )
        for review, product, customer in result.all()
    ]

def _resolve_review_name(name) -> str:
    if isinstance(name, dict):
        return name.get('en') or next(iter(name.values()), '')
    return str(name)

async def list_product_reviews_service(tenant_slug: str, product_slug: str, db: AsyncSession) -> list[ProductReviewResponse]:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    product_result = await db.execute(
        select(Product).where(Product.slug == product_slug, Product.tenant_id == tenant_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = await db.execute(
        select(ProductReview, User)
        .join(User, User.id == ProductReview.user_id)
        .where(
            ProductReview.tenant_id == tenant_id,
            ProductReview.product_id == product.id,
            ProductReview.is_approved == True,
        )
        .order_by(ProductReview.created_at.desc())
    )

    return [
        ProductReviewResponse(
            id=review.id,
            product_id=review.product_id,
            product_name=_resolve_review_name(product.name),
            user_id=review.user_id,
            customer_name=customer.full_name,
            rating=review.rating,
            comment=review.comment,
            is_approved=review.is_approved,
            is_verified_buyer=review.is_verified_buyer,
            created_at=review.created_at,
        )
        for review, customer in result.all()
    ]

async def create_product_review_service(
    tenant_slug: str, user_id: int, req: ProductReviewCreateRequest, db: AsyncSession
) -> ProductReviewResponse:
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_slug).options(selectinload(Tenant.settings))
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    product_result = await db.execute(
        select(Product).where(Product.id == req.product_id, Product.tenant_id == tenant.id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = await db.execute(
        select(ProductReview).where(
            ProductReview.tenant_id == tenant.id,
            ProductReview.product_id == req.product_id,
            ProductReview.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    purchase_result = await db.execute(
        select(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(ProductVariant, ProductVariant.id == OrderItem.variant_id)
        .where(
            Order.tenant_id == tenant.id,
            Order.user_id == user_id,
            Order.status.in_(('processing', 'completed')),
            ProductVariant.product_id == req.product_id,
        )
    )
    is_verified_buyer = purchase_result.first() is not None

    moderation_enabled = tenant.settings.review_moderation_enabled if tenant.settings else False

    review = ProductReview(
        tenant_id=tenant.id,
        product_id=req.product_id,
        user_id=user_id,
        rating=req.rating,
        comment=req.comment,
        is_approved=not moderation_enabled,
        is_verified_buyer=is_verified_buyer,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    user_result = await db.execute(select(User).where(User.id == user_id))
    customer = user_result.scalar_one()

    return ProductReviewResponse(
        id=review.id,
        product_id=review.product_id,
        product_name=_resolve_review_name(product.name),
        user_id=review.user_id,
        customer_name=customer.full_name,
        rating=review.rating,
        comment=review.comment,
        is_approved=review.is_approved,
        is_verified_buyer=review.is_verified_buyer,
        created_at=review.created_at,
    )

async def export_orders_csv_service(tenant_slug: str, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(Order, User)
        .join(User, User.id == Order.user_id)
        .where(Order.tenant_id == tenant_id)
        .order_by(Order.created_at.desc())
    )

    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(["order_id", "order_number", "customer_name", "customer_email", "status", "total", "created_at"])
    for order, customer in result.all():
        writer.writerow([
            order.id, order.order_number, customer.full_name, customer.email,
            order.status, order.total_amount, order.created_at,
        ])

    f.seek(0)
    return StreamingResponse(f, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

async def get_inventory_health_service(tenant_slug: str, db: AsyncSession) -> InventoryHealthResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(ProductVariant, Product)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(ProductVariant.tenant_id == tenant_id, Product.is_active == True)
        .order_by(ProductVariant.stock_quantity.asc())
    )

    out_of_stock = []
    low_stock = []
    for variant, product in result.all():
        item = InventoryHealthItem(
            product_id=product.id,
            product_name=product.name,
            variant_id=variant.id,
            sku=variant.sku,
            stock_quantity=variant.stock_quantity,
        )
        if variant.stock_quantity <= 0:
            out_of_stock.append(item)
        elif variant.stock_quantity <= LOW_STOCK_THRESHOLD:
            low_stock.append(item)

    return InventoryHealthResponse(
        low_stock_threshold=LOW_STOCK_THRESHOLD, out_of_stock=out_of_stock, low_stock=low_stock
    )
