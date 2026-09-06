"""Store-visibility completeness: all product fields + every supported language.

A store manager can opt in (`require_product_completeness`). A platform admin
can hard-lock the same rule (`force_product_completeness`). Either flag means
an incomplete product cannot enter the public store or marketplace.
"""
from typing import Any, Iterable, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Product
from app.models.tenant import TenantSettings
from app.services.i18n_utils import validate_i18n


def completeness_required(settings: TenantSettings | None) -> bool:
    if settings is None:
        return False
    return bool(settings.require_product_completeness or settings.force_product_completeness)


def supported_languages_of(settings: TenantSettings | None) -> list[str]:
    langs = getattr(settings, "supported_languages", None) if settings else None
    return list(langs) if langs else ["he"]


def missing_i18n_langs(field_dict: Any, supported_langs: Sequence[str]) -> list[str]:
    if not isinstance(field_dict, dict):
        return list(supported_langs)
    return [
        lang
        for lang in supported_langs
        if lang not in field_dict or not str(field_dict[lang]).strip()
    ]


def product_completeness_gaps(
    *,
    name: Any,
    description: Any,
    slug: Any,
    base_price: Any,
    product_type: str | None,
    digital_file_url: Any,
    variant_skus: Iterable[str | None],
    image_urls: Iterable[str | None],
    supported_langs: Sequence[str],
) -> list[str]:
    gaps: list[str] = []
    missing_name = missing_i18n_langs(name, supported_langs)
    if missing_name:
        gaps.append(f"name translations: {missing_name}")
    missing_desc = missing_i18n_langs(description, supported_langs)
    if missing_desc:
        gaps.append(f"description translations: {missing_desc}")
    if not slug or not str(slug).strip():
        gaps.append("slug")
    try:
        if base_price is None or float(base_price) <= 0:
            gaps.append("base_price")
    except (TypeError, ValueError):
        gaps.append("base_price")
    if not any(sku and str(sku).strip() for sku in variant_skus):
        gaps.append("at least one variant with a SKU")
    if not any(url and str(url).strip() for url in image_urls):
        gaps.append("at least one image")
    if product_type == "digital" and (not digital_file_url or not str(digital_file_url).strip()):
        gaps.append("digital_file_url")
    return gaps


def gaps_for_product(product: Product, supported_langs: Sequence[str]) -> list[str]:
    return product_completeness_gaps(
        name=product.name,
        description=product.description,
        slug=product.slug,
        base_price=product.base_price,
        product_type=product.product_type,
        digital_file_url=product.digital_file_url,
        variant_skus=[v.sku for v in (product.variants or [])],
        image_urls=[img.image_url for img in (product.images or [])],
        supported_langs=supported_langs,
    )


def raise_if_cannot_enter_store(gaps: list[str]) -> None:
    if gaps:
        raise HTTPException(
            status_code=422,
            detail=f"Product is incomplete and cannot enter the store. Missing: {gaps}",
        )


def product_is_store_eligible(product: Product, settings: TenantSettings | None) -> bool:
    if not getattr(product, "is_active", False):
        return False
    if not completeness_required(settings):
        return True
    return not gaps_for_product(product, supported_languages_of(settings))


async def assert_store_eligible_or_404(db: AsyncSession, product: Product) -> None:
    result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == product.tenant_id))
    if not product_is_store_eligible(product, result.scalar_one_or_none()):
        raise HTTPException(status_code=404, detail="Variant not found or product inactive")


async def deactivate_incomplete_store_products(
    db: AsyncSession, tenant_id: int, settings: TenantSettings | None
) -> int:
    if not completeness_required(settings):
        return 0
    langs = supported_languages_of(settings)
    result = await db.execute(
        select(Product)
        .where(Product.tenant_id == tenant_id, Product.is_active.is_(True))
        .options(selectinload(Product.variants), selectinload(Product.images))
    )
    deactivated = 0
    for product in result.scalars().unique().all():
        if gaps_for_product(product, langs):
            product.is_active = False
            deactivated += 1
    return deactivated


def validate_nav_labels(nav_items: Any, supported_langs: Sequence[str]) -> None:
    if not nav_items:
        return
    for item in nav_items:
        if isinstance(item, dict):
            label = item.get("label")
            item_id = item.get("id", "item")
        else:
            label = getattr(item, "label", None)
            item_id = getattr(item, "id", "item")
        validate_i18n(label or {}, list(supported_langs), f"nav_items[{item_id}].label")
