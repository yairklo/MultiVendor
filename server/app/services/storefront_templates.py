"""
Definitions for the 3 built-in premium storefront templates. Deliberately just plain Python
data structured exactly like the `sections` array `update_page_sections`/upsert_page_sections_service
already accepts — applying a template is nothing more than calling the same upsert path 3 times
(once per page_key below) with one of these dicts, which is what makes the result immediately
editable by the AI agent through its existing tools: it's just another StorePage row to it.

Imagery is Lorem Picsum placeholder photography (deterministic by seed, always resolves) — sellers
are expected to swap it for real product photography via the AI chat or admin editor.

STOREFRONT_TEMPLATES below is the shipped set of *built-in* templates: their content lives here in
Python and is seeded into the `storefront_templates` table by Alembic migration 0002 (and mirrored
into db/seed.sql for the test DB). It is NOT the live source the running app reads from -- that's
the `StorefrontTemplate` DB table (see app/models/storefront_template.py), which is what
list_storefront_template_metas/get_storefront_template below query. That split is what makes adding
a 4th template, or editing swatch/copy on an existing one, a DB write instead of a code deploy;
STOREFRONT_TEMPLATES here stays purely as the canonical definition of the 3 templates that ship
with the app (used to generate the seed data, and validated by
test_every_storefront_template_page_is_schema_valid).
"""
from typing import Any, Dict, List, TypedDict

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storefront_template import StorefrontTemplate as StorefrontTemplateRow
from app.schemas.ai_schemas import Section


class StorefrontTemplateMeta(TypedDict):
    key: str
    name: str
    tagline: str
    swatch: Dict[str, str]


class StorefrontTemplate(StorefrontTemplateMeta):
    pages: Dict[str, Dict[str, Any]]


def _picsum(seed: str, w: int = 1600, h: int = 900) -> str:
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"


AURORA: StorefrontTemplate = {
    "key": "aurora",
    "name": "Aurora",
    "tagline": "Soft, minimal, boutique-ready.",
    "swatch": {"bg": "#faf8f5", "text": "#1f2937", "accent": "#6366f1"},
    "pages": {
        "home": {
            "title": "Home",
            "background_color": "#faf8f5",
            "text_color": "#1f2937",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {
                        "headline": "Timeless pieces, thoughtfully made",
                        "size": "large",
                        "alignment": "center",
                        "background_color": "#f1ede7",
                        "text_color": "#1f2937",
                    },
                    "media": {"type": "image", "url": _picsum("aurora-hero"), "aspect_ratio": "16/9"},
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "Why shop with us",
                        "items": [
                            {"icon": "Truck", "title": "Free shipping", "text": "On every order, no minimum spend."},
                            {"icon": "ShieldCheck", "title": "Secure checkout", "text": "Your payment details always stay protected."},
                            {"icon": "RotateCcw", "title": "30-day returns", "text": "Not quite right? Send it back, no questions asked."},
                        ],
                    },
                },
                {
                    "type": "product_grid",
                    "settings": {"title": "New Arrivals", "columns": 4, "card_style": "minimal"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "muted"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "Our story",
                                    "body": (
                                        "We started with a simple idea: fewer, better things. Every piece in "
                                        "our collection is chosen for how it's made, not just how it looks — "
                                        "small runs, honest materials, and a supply chain we can actually stand behind."
                                    ),
                                },
                            },
                        ],
                        "right": [
                            {
                                "type": "gallery",
                                "settings": {
                                    "layout": "grid",
                                    "images": [_picsum("aurora-gallery-1", 800, 800), _picsum("aurora-gallery-2", 800, 800)],
                                },
                            },
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "settings": {
                        "title": "Loved by our customers",
                        "items": [
                            {"quote": "The quality is unreal for the price. My new go-to store.", "author": "Maya R.", "role": "Verified buyer"},
                            {"quote": "Fast shipping and the packaging alone felt premium.", "author": "Daniel K.", "role": "Verified buyer"},
                            {"quote": "Customer support actually helped me pick the right size.", "author": "Sarah L.", "role": "Verified buyer"},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [
                            {"label": "Shop the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}},
                            {"label": "Our story", "variant": "outline", "actionType": "NAVIGATE", "actionPayload": {"page_key": "about"}},
                        ]
                    },
                },
            ],
        },
        "about": {
            "title": "About",
            "background_color": "#faf8f5",
            "text_color": "#1f2937",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {"headline": "About us", "size": "small", "alignment": "center", "background_color": "#f1ede7"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "neutral"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "How it started",
                                    "body": (
                                        "We opened our doors because we couldn't find what we wanted to buy "
                                        "ourselves — thoughtfully designed, well made, and priced fairly. "
                                        "Today every product is still picked (or made) by our small team, one "
                                        "collection at a time."
                                    ),
                                },
                            },
                        ],
                        "right": [
                            {"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("aurora-about-1", 800, 800)]}},
                        ],
                    },
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "What we care about",
                        "items": [
                            {"icon": "Leaf", "title": "Sustainability", "text": "Responsibly sourced materials wherever we can."},
                            {"icon": "Award", "title": "Craftsmanship", "text": "Small batches, checked by hand."},
                            {"icon": "Heart", "title": "Community", "text": "A portion of every sale supports local makers."},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [{"label": "Shop the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]
                    },
                },
            ],
        },
        "contact": {
            "title": "Contact",
            "background_color": "#faf8f5",
            "text_color": "#1f2937",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {"headline": "Get in touch", "size": "small", "alignment": "center", "background_color": "#f1ede7"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "neutral"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "We'd love to hear from you",
                                    "body": "Email hello@yourstore.com and we'll get back to you within one business day.",
                                },
                            },
                        ],
                        "right": [
                            {
                                "type": "table",
                                "settings": {
                                    "title": "Support hours",
                                    "headers": ["Day", "Hours"],
                                    "rows": [["Mon – Fri", "9:00 – 18:00"], ["Saturday", "10:00 – 16:00"], ["Sunday", "Closed"]],
                                },
                            },
                        ],
                    },
                },
            ],
        },
    },
}

ATELIER: StorefrontTemplate = {
    "key": "atelier",
    "name": "Atelier",
    "tagline": "Dark, editorial, high-fashion.",
    "swatch": {"bg": "#15130f", "text": "#f5f0e6", "accent": "#c9a24b"},
    "pages": {
        "home": {
            "title": "Home",
            "background_color": "#15130f",
            "text_color": "#f5f0e6",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {
                        "headline": "Crafted for those who notice the details",
                        "size": "large",
                        "alignment": "left",
                        "background_color": "#1f1c16",
                        "text_color": "#f5f0e6",
                    },
                    "media": {"type": "image", "url": _picsum("atelier-hero"), "aspect_ratio": "16/9"},
                },
                {
                    "type": "product_grid",
                    "settings": {"title": "Bestsellers", "columns": 3, "card_style": "framed"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "secondary"},
                    "zones": {
                        "left": [
                            {"type": "gallery", "settings": {"layout": "carousel", "images": [_picsum("atelier-gallery-1", 900, 900), _picsum("atelier-gallery-2", 900, 900), _picsum("atelier-gallery-3", 900, 900)]}},
                        ],
                        "right": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "The atelier",
                                    "body": (
                                        "Every collection begins on a workbench, not a spreadsheet. We work in "
                                        "small runs with artisans we've partnered with for years, so every "
                                        "piece carries a little more weight than the price tag suggests."
                                    ),
                                    "background_color": "#1f1c16",
                                    "text_color": "#f5f0e6",
                                },
                            },
                        ],
                    },
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "The Atelier promise",
                        "items": [
                            {"icon": "Award", "title": "Limited runs", "text": "Small batches, never mass-produced."},
                            {"icon": "PackageCheck", "title": "Gift-ready packaging", "text": "Every order arrives ready to give."},
                            {"icon": "Headphones", "title": "Personal styling", "text": "Message us for one-to-one advice."},
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "settings": {
                        "title": "In their words",
                        "items": [
                            {"quote": "Feels like a piece I'll still be wearing in ten years.", "author": "Noa B.", "role": "Verified buyer"},
                            {"quote": "The packaging alone made it feel like an occasion.", "author": "Itay G.", "role": "Verified buyer"},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "background_color": "#1f1c16",
                        "buttons": [
                            {"label": "Explore the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}},
                        ],
                    },
                },
            ],
        },
        "about": {
            "title": "About",
            "background_color": "#15130f",
            "text_color": "#f5f0e6",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "About the atelier", "size": "small", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}},
                {
                    "type": "text_block",
                    "settings": {
                        "heading": "A house built on craft",
                        "body": (
                            "Founded by a small group of designers who wanted to slow things down, we work "
                            "directly with artisan workshops instead of factories. It costs more and takes "
                            "longer — we think that's the point."
                        ),
                        "background_color": "#1f1c16",
                        "text_color": "#f5f0e6",
                    },
                },
                {"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("atelier-about-1", 800, 800), _picsum("atelier-about-2", 800, 800)]}},
                {
                    "type": "button_group",
                    "settings": {
                        "background_color": "#1f1c16",
                        "buttons": [{"label": "Explore the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}],
                    },
                },
            ],
        },
        "contact": {
            "title": "Contact",
            "background_color": "#15130f",
            "text_color": "#f5f0e6",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "Contact the atelier", "size": "small", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}},
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "secondary"},
                    "zones": {
                        "left": [{"type": "text_block", "settings": {"heading": "Reach us", "body": "hello@yourstore.com — private styling appointments available on request.", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}],
                        "right": [{"type": "table", "settings": {"title": "Studio hours", "headers": ["Day", "Hours"], "rows": [["Tue – Sat", "11:00 – 19:00"], ["Sun – Mon", "By appointment"]]}}],
                    },
                },
            ],
        },
    },
}

NOVA: StorefrontTemplate = {
    "key": "nova",
    "name": "Nova",
    "tagline": "Bold, vivid, modern.",
    "swatch": {"bg": "#ffffff", "text": "#111827", "accent": "#f0653a"},
    "pages": {
        "home": {
            "title": "Home",
            "background_color": "#ffffff",
            "text_color": "#111827",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {
                        "headline": "Everyday gear, leveled up",
                        "size": "large",
                        "alignment": "center",
                        "background_color": "#fff1ec",
                        "text_color": "#111827",
                    },
                    "media": {"type": "image", "url": _picsum("nova-hero"), "aspect_ratio": "16/9"},
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "Why you'll love it here",
                        "items": [
                            {"icon": "Truck", "title": "Fast shipping", "text": "Most orders ship within 24 hours."},
                            {"icon": "CreditCard", "title": "Flexible payment", "text": "Pay in full or split it up."},
                            {"icon": "Sparkles", "title": "New drops weekly", "text": "Fresh product every single week."},
                        ],
                    },
                },
                {
                    "type": "product_grid",
                    "settings": {"title": "Trending now", "columns": 4, "card_style": "default"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "accent"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "Built different",
                                    "body": "We obsess over the details other stores skip — real materials, real testing, real reviews.",
                                },
                            },
                        ],
                        "right": [
                            {"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("nova-gallery-1", 800, 800), _picsum("nova-gallery-2", 800, 800)]}},
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "settings": {
                        "title": "What people say",
                        "items": [
                            {"quote": "Ordered on Monday, wearing it by Wednesday. Insane.", "author": "Tom H.", "role": "Verified buyer"},
                            {"quote": "Finally a store that doesn't feel like every other store.", "author": "Priya S.", "role": "Verified buyer"},
                            {"quote": "The quality shocked me for this price point.", "author": "Alex M.", "role": "Verified buyer"},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [
                            {"label": "Shop now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}},
                            {"label": "About us", "variant": "outline", "actionType": "NAVIGATE", "actionPayload": {"page_key": "about"}},
                        ]
                    },
                },
            ],
        },
        "about": {
            "title": "About",
            "background_color": "#ffffff",
            "text_color": "#111827",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "About us", "size": "small", "alignment": "center", "background_color": "#fff1ec"}},
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "muted"},
                    "zones": {
                        "left": [{"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("nova-about-1", 800, 800)]}}],
                        "right": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "Why we exist",
                                    "body": "We got tired of choosing between good design and a fair price — so we built a store that doesn't make you choose.",
                                },
                            },
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {"buttons": [{"label": "Shop now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]},
                },
            ],
        },
        "contact": {
            "title": "Contact",
            "background_color": "#ffffff",
            "text_color": "#111827",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "Talk to us", "size": "small", "alignment": "center", "background_color": "#fff1ec"}},
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "muted"},
                    "zones": {
                        "left": [{"type": "text_block", "settings": {"heading": "Say hello", "body": "hello@yourstore.com — we usually reply the same day."}}],
                        "right": [{"type": "table", "settings": {"title": "Support hours", "headers": ["Day", "Hours"], "rows": [["Mon – Fri", "9:00 – 20:00"], ["Weekends", "10:00 – 15:00"]]}}],
                    },
                },
            ],
        },
    },
}

STOREFRONT_TEMPLATES: List[StorefrontTemplate] = [AURORA, ATELIER, NOVA]
STOREFRONT_TEMPLATES_BY_KEY: Dict[str, StorefrontTemplate] = {t["key"]: t for t in STOREFRONT_TEMPLATES}
# The three templates that ship with the app: they can be deactivated, never deleted.
BUILTIN_TEMPLATE_KEYS = frozenset({"aurora", "atelier", "nova"})


def validate_swatch_json(swatch: Any) -> None:
    if not isinstance(swatch, dict):
        raise HTTPException(status_code=422, detail="swatch_json must be an object")
    for key in ("bg", "text", "accent"):
        value = swatch.get(key)
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(status_code=422, detail=f"swatch_json.{key} is required")


def validate_storefront_template_pages(pages: Any) -> None:
    """Same section-schema check as test_every_storefront_template_page_is_schema_valid.

    Every page must have a non-empty `sections` list, and every section must construct
    as `Section(**s)` (type, nested children/zones, media, etc.).
    """
    if not isinstance(pages, dict) or not pages:
        raise HTTPException(
            status_code=422,
            detail="pages_json must be a non-empty object mapping page_key to page content",
        )
    for page_key, page_content in pages.items():
        if not isinstance(page_key, str) or not page_key.strip():
            raise HTTPException(status_code=422, detail="pages_json keys must be non-empty page keys")
        if not isinstance(page_content, dict):
            raise HTTPException(status_code=422, detail=f"pages_json[{page_key}] must be an object")
        raw_sections = page_content.get("sections")
        if not isinstance(raw_sections, list) or len(raw_sections) == 0:
            raise HTTPException(status_code=422, detail=f"{page_key} has no sections")
        try:
            parsed = [Section(**s) for s in raw_sections]
        except (ValidationError, TypeError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"{page_key} sections failed schema validation",
            ) from exc
        if len(parsed) == 0:
            raise HTTPException(status_code=422, detail=f"{page_key} has no sections")


def template_row_to_admin_dict(row: StorefrontTemplateRow) -> Dict[str, Any]:
    return {
        "id": row.id,
        "template_key": row.template_key,
        "name": row.name,
        "tagline": row.tagline,
        "swatch_json": row.swatch_json,
        "pages_json": row.pages_json,
        "display_order": row.display_order,
        "is_active": bool(row.is_active),
        "is_builtin": row.template_key in BUILTIN_TEMPLATE_KEYS,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def list_storefront_template_metas(db: AsyncSession) -> List[StorefrontTemplateMeta]:
    result = await db.execute(
        select(StorefrontTemplateRow)
        .where(StorefrontTemplateRow.is_active == True)
        .order_by(StorefrontTemplateRow.display_order)
    )
    rows = result.scalars().all()
    return [{"key": r.template_key, "name": r.name, "tagline": r.tagline, "swatch": r.swatch_json} for r in rows]


async def get_storefront_template(template_key: str, db: AsyncSession) -> StorefrontTemplate | None:
    result = await db.execute(
        select(StorefrontTemplateRow).where(StorefrontTemplateRow.template_key == template_key)
    )
    row = result.scalar_one_or_none()
    if not row:
        return None
    return {"key": row.template_key, "name": row.name, "tagline": row.tagline, "swatch": row.swatch_json, "pages": row.pages_json}


async def list_all_storefront_templates(db: AsyncSession) -> List[StorefrontTemplateRow]:
    """Super-admin catalog — includes inactive templates. Tenant-facing list stays active-only."""
    result = await db.execute(
        select(StorefrontTemplateRow).order_by(
            StorefrontTemplateRow.display_order,
            StorefrontTemplateRow.id,
        )
    )
    return list(result.scalars().all())


async def get_storefront_template_row(template_key: str, db: AsyncSession) -> StorefrontTemplateRow | None:
    result = await db.execute(
        select(StorefrontTemplateRow).where(StorefrontTemplateRow.template_key == template_key)
    )
    return result.scalar_one_or_none()


async def create_storefront_template(
    *,
    template_key: str,
    name: str,
    tagline: str,
    swatch_json: Dict[str, Any],
    pages_json: Dict[str, Any],
    display_order: int,
    db: AsyncSession,
) -> StorefrontTemplateRow:
    validate_swatch_json(swatch_json)
    validate_storefront_template_pages(pages_json)
    row = StorefrontTemplateRow(
        template_key=template_key,
        name=name,
        tagline=tagline,
        swatch_json=swatch_json,
        pages_json=pages_json,
        display_order=display_order,
        is_active=True,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="template_key already exists")
    await db.refresh(row)
    return row


async def update_storefront_template(
    template_key: str,
    *,
    name: str,
    tagline: str,
    swatch_json: Dict[str, Any],
    pages_json: Dict[str, Any],
    display_order: int | None,
    db: AsyncSession,
) -> StorefrontTemplateRow:
    row = await get_storefront_template_row(template_key, db)
    if not row:
        raise HTTPException(status_code=404, detail="Storefront template not found")
    validate_swatch_json(swatch_json)
    validate_storefront_template_pages(pages_json)
    row.name = name
    row.tagline = tagline
    row.swatch_json = swatch_json
    row.pages_json = pages_json
    if display_order is not None:
        row.display_order = display_order
    await db.commit()
    await db.refresh(row)
    return row


async def patch_storefront_template(
    template_key: str,
    *,
    is_active: bool | None,
    display_order: int | None,
    db: AsyncSession,
) -> StorefrontTemplateRow:
    row = await get_storefront_template_row(template_key, db)
    if not row:
        raise HTTPException(status_code=404, detail="Storefront template not found")
    if is_active is not None:
        row.is_active = is_active
    if display_order is not None:
        row.display_order = display_order
    await db.commit()
    await db.refresh(row)
    return row
