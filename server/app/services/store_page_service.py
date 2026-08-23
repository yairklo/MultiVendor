import secrets
from typing import Any, Dict, List, Tuple

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenant import Tenant, TenantSettings
from app.models.store_page import StorePage, StorePageVersion
from app.schemas.ai_schemas import (
    StorePageSchema, StorePageSummary, StorePageVersionSummary, Section,
    SECTION_TYPES, BUTTON_ACTION_TYPES, BUTTON_VARIANTS, CONTAINER_SECTION_TYPES,
    DESIGN_VARIANTS, CARD_STYLES, MAX_SECTION_NESTING_DEPTH,
)
from app.services.storefront_templates import (
    StorefrontTemplateMeta, get_storefront_template, list_storefront_template_metas,
)
from app.services.i18n_utils import validate_i18n

# Scalar (single-string) text fields per section type -- each becomes
# {"en": "...", "he": "...", ...} instead of a plain string. Array/object
# text fields (testimonials/feature_highlights items, button labels, table
# cells) are handled separately below since they're not flat key lookups.
SECTION_SCALAR_TEXT_FIELDS: Dict[str, List[str]] = {
    "hero_banner": ["headline"],
    "text_block": ["heading", "body"],
    "testimonials": ["title"],
    "feature_highlights": ["title"],
    "gallery": ["title"],
    "video_embed": ["title"],
    "product_grid": ["title"],
    "table": ["title"],
}

# section type -> (settings key holding the array, text field names within each item)
SECTION_ITEM_TEXT_FIELDS: Dict[str, Tuple[str, List[str]]] = {
    "testimonials": ("items", ["quote", "author", "role"]),
    "feature_highlights": ("items", ["title", "text"]),
    "button_group": ("buttons", ["label"]),
}

MAX_VERSIONS_PER_PAGE = 20

# 'global' is reserved by the AI copilot as the sentinel meaning "no real page"
# (see ai_conversation_service / ai_agent_service) — never a legitimate page_key.
# Blocked here, not just relied on as a frontend convention, so a prompt/agent
# regression that reintroduces it fails loudly instead of silently creating a
# phantom StorePage row that then pollutes the real page picker.
RESERVED_PAGE_KEYS = {"global"}


async def _get_tenant_id(tenant_slug: str, db: AsyncSession) -> int:
    result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


def _to_schema(page: StorePage) -> StorePageSchema:
    """Draft view — what the AI and the admin preview read. Never shown to shoppers."""
    has_unpublished_changes = page.published_at is None or (
        page.updated_at is not None and page.updated_at > page.published_at
    )
    return StorePageSchema(
        page_key=page.page_key,
        page_type=page.page_type,
        title=page.title,
        sections=[Section(**s) for s in (page.sections or [])],
        background_color=page.background_color,
        text_color=page.text_color,
        has_unpublished_changes=has_unpublished_changes,
        published_at=page.published_at,
    )


def _to_published_schema(page: StorePage) -> StorePageSchema:
    """Published view — the only thing the public storefront is ever allowed to read."""
    if page.published_at is None:
        raise HTTPException(
            status_code=404, detail=f"No published page found for page_key='{page.page_key}' page_type='{page.page_type}'"
        )
    return StorePageSchema(
        page_key=page.page_key,
        page_type=page.page_type,
        title=page.published_title or page.title,
        sections=[Section(**s) for s in (page.published_sections or [])],
        background_color=page.published_background_color,
        text_color=page.published_text_color,
    )


_SAFE_URL_SCHEMES = {"http", "https", "mailto"}


def _sanitize_url(url: Any) -> "str | None":
    """
    Clamps a free-text URL (a button's actionPayload.href, a section's
    media.url) to a safe allow-list — http(s), mailto, or a relative/anchor
    link — the same "strip it, don't guess" enforcement pattern as
    _sanitize_design_variant_settings/_sanitize_card_style_settings below. An
    AI-authored or hallucinated 'javascript:'/'data:'/'vbscript:' URL is
    dropped entirely rather than ever reaching the storefront.
    """
    if not isinstance(url, str) or not url.strip():
        return None
    url = url.strip()
    if url.startswith("/") or url.startswith("#"):
        return url
    scheme = url.split(":", 1)[0].lower() if ":" in url else ""
    return url if scheme in _SAFE_URL_SCHEMES else None


def _sanitize_action_payload_href(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "href" not in payload:
        return payload
    safe_href = _sanitize_url(payload.get("href"))
    if safe_href is None:
        return {k: v for k, v in payload.items() if k != "href"}
    return {**payload, "href": safe_href}


def _sanitize_button_group_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    button_group is the one section type that drives runtime behavior (a click
    dispatches actionType/actionPayload), so unlike other settings we don't just
    pass it through — any button with an actionType outside the fixed allow-list
    is dropped before it's ever persisted, so the AI can never smuggle an
    unrecognized action through to the frontend. actionPayload.href specifically
    also gets scheme-checked via _sanitize_url, since it's the one free-text URL
    a click can actually navigate to.
    """
    buttons = settings.get("buttons")
    buttons = buttons if isinstance(buttons, list) else []
    sanitized = []
    for b in buttons:
        if not isinstance(b, dict):
            continue
        # label is a localized {lang: text} dict (see _sanitize_section_text, which runs
        # after this and enforces every supported language is present) -- a legacy plain
        # string is also accepted here since it's what auto-upgrades on that later pass.
        if not b.get("label") or b.get("actionType") not in BUTTON_ACTION_TYPES:
            continue
        entry = {
            "label": b["label"],
            "variant": b.get("variant") if b.get("variant") in BUTTON_VARIANTS else "primary",
            "actionType": b["actionType"],
        }
        if isinstance(b.get("actionPayload"), dict):
            entry["actionPayload"] = _sanitize_action_payload_href(b["actionPayload"])
        sanitized.append(entry)
    return {**settings, "buttons": sanitized}


def _sanitize_design_variant_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp a container's design_variant to the fixed token allow-list — this is the real
    enforcement gate; the frontend's own fallback-to-neutral lookup is defense-in-depth, not
    the primary guarantee that only a Tailwind-generated class ever reaches the DOM."""
    variant = settings.get("design_variant")
    if variant not in DESIGN_VARIANTS:
        return {k: v for k, v in settings.items() if k != "design_variant"}
    return settings


def _sanitize_card_style_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Clamp a product_grid's card_style to the fixed allow-list, same rationale/pattern as
    _sanitize_design_variant_settings — lets the AI restyle product cards without ever letting
    it emit a value the frontend's literal Tailwind class map (product-card-styles.ts) doesn't
    recognize (which the frontend would just fall back to 'default' for anyway; this is the
    real enforcement gate)."""
    style = settings.get("card_style")
    if style not in CARD_STYLES:
        return {k: v for k, v in settings.items() if k != "card_style"}
    return settings


def _localize_value(value: Any, supported_langs: List[str]) -> Any:
    """Auto-upgrades a legacy plain-string value (every section saved before
    per-language text existed, plus every premium template's hardcoded
    single-language copy -- see apply_storefront_template_service) to the
    same text duplicated under every supported language, in place.

    Deliberately NOT "put it under default_language only and force the rest
    to be filled in" -- that would make re-saving any pre-existing page, or
    applying a template to a multi-language store, fail outright with a 422
    the moment this feature shipped. Duplicating means nothing is ever
    blank/broken and old content keeps saving; the store owner then narrows
    a language down to a real translation via the editor's language tabs
    whenever they get to it. Enforcement (validate_i18n below) still does
    real work going forward: once a field is genuinely {lang: text} and an
    admin clears one language's tab, that language is missing again and the
    save is rejected -- it just doesn't retroactively punish content nobody
    has touched since this shipped."""
    return {lang: value for lang in supported_langs} if isinstance(value, str) else value


def _validate_and_upgrade_text_field(
    container: Dict[str, Any], field: str, supported_langs: List[str]
) -> None:
    if field not in container or container[field] is None:
        return
    container[field] = _localize_value(container[field], supported_langs)
    validate_i18n(container[field], supported_langs, field)


def _sanitize_section_text(settings: Dict[str, Any], section_type: str, supported_langs: List[str]) -> None:
    """Mutates `settings` in place: upgrades any legacy plain-string text field to
    {lang: text} and enforces every supported language is present, for every text
    field this section type carries -- scalars, item-array fields, and (table only)
    the header/row cell arrays."""
    for field in SECTION_SCALAR_TEXT_FIELDS.get(section_type, []):
        _validate_and_upgrade_text_field(settings, field, supported_langs)

    if section_type in SECTION_ITEM_TEXT_FIELDS:
        array_key, item_fields = SECTION_ITEM_TEXT_FIELDS[section_type]
        items = settings.get(array_key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for field in item_fields:
                        _validate_and_upgrade_text_field(item, field, supported_langs)

    if section_type == "table":
        headers = settings.get("headers")
        if isinstance(headers, list):
            settings["headers"] = [_localize_value(h, supported_langs) for h in headers]
            for i, cell in enumerate(settings["headers"]):
                validate_i18n(cell, supported_langs, f"headers[{i}]")

        rows = settings.get("rows")
        if isinstance(rows, list):
            new_rows = []
            for r, row in enumerate(rows):
                if not isinstance(row, list):
                    new_rows.append(row)
                    continue
                new_row = [_localize_value(cell, supported_langs) for cell in row]
                for c, cell in enumerate(new_row):
                    validate_i18n(cell, supported_langs, f"rows[{r}][{c}]")
                new_rows.append(new_row)
            settings["rows"] = new_rows


def _sanitize_sections(
    raw_sections: List[Dict[str, Any]], supported_langs: List[str],
    seen_ids: "set | None" = None, depth: int = 0,
) -> List[Dict[str, Any]]:
    # A single seen_ids set is threaded through every recursive call (never recreated per
    # call) so generated ids stay globally unique across nesting levels, not just within one.
    if seen_ids is None:
        seen_ids = set()
    if depth > MAX_SECTION_NESTING_DEPTH:
        raise HTTPException(status_code=400, detail="Section nesting too deep")

    sanitized: List[Dict[str, Any]] = []
    for raw in raw_sections:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail=f"Each section must be an object with a 'type' field, got: {raw!r}")
        section_type = raw.get("type")
        if section_type not in SECTION_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid section type: {section_type}")

        section_id = raw.get("id")
        if not isinstance(section_id, str) or not section_id.strip() or section_id in seen_ids:
            section_id = f"sec_{secrets.token_hex(4)}"
        seen_ids.add(section_id)

        settings = raw.get("settings") or {}
        if section_type == "button_group":
            settings = _sanitize_button_group_settings(settings)
        elif section_type in CONTAINER_SECTION_TYPES:
            settings = _sanitize_design_variant_settings(settings)
        elif section_type == "product_grid":
            settings = _sanitize_card_style_settings(settings)

        _sanitize_section_text(settings, section_type, supported_langs)

        entry: Dict[str, Any] = {"id": section_id, "type": section_type, "settings": settings}
        media = raw.get("media")
        if isinstance(media, dict):
            # A media block with no safe url is dropped whole, not persisted
            # with a broken/dangerous url — no section should ever end up
            # pointing at a partial or unsafe media reference.
            safe_url = _sanitize_url(media.get("url"))
            if safe_url is not None:
                entry["media"] = {**media, "url": safe_url}

        if section_type == "grid_container":
            children = raw.get("children") if isinstance(raw.get("children"), list) else []
            entry["children"] = _sanitize_sections(children, supported_langs, seen_ids, depth + 1)
        elif section_type == "two_column_layout":
            zones_raw = raw.get("zones") if isinstance(raw.get("zones"), dict) else {}
            entry["zones"] = {
                zone: _sanitize_sections(items, supported_langs, seen_ids, depth + 1)
                for zone, items in zones_raw.items()
                if zone in ("left", "right") and isinstance(items, list)
            }

        sanitized.append(entry)
    return sanitized


async def _snapshot_version(page: StorePage, db: AsyncSession) -> None:
    """
    Saves the page's state as it is *right now*, before the caller applies a new
    change to it — called on every edit to an existing page, never on first
    creation (there's nothing to go back to yet). Keeps only the most recent
    MAX_VERSIONS_PER_PAGE snapshots so chatty AI edits don't grow this table
    unbounded.
    """
    db.add(StorePageVersion(
        store_page_id=page.id,
        tenant_id=page.tenant_id,
        page_key=page.page_key,
        page_type=page.page_type,
        title=page.title,
        sections=page.sections,
        background_color=page.background_color,
        text_color=page.text_color,
    ))
    await db.flush()

    old_ids_result = await db.execute(
        select(StorePageVersion.id)
        .where(StorePageVersion.store_page_id == page.id)
        .order_by(StorePageVersion.created_at.desc(), StorePageVersion.id.desc())
        .offset(MAX_VERSIONS_PER_PAGE)
    )
    old_ids = [row[0] for row in old_ids_result.all()]
    if old_ids:
        await db.execute(delete(StorePageVersion).where(StorePageVersion.id.in_(old_ids)))


async def list_page_versions_service(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> List[StorePageVersionSummary]:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(StorePageVersion)
        .where(
            StorePageVersion.tenant_id == tenant_id,
            StorePageVersion.page_key == page_key,
            StorePageVersion.page_type == page_type,
        )
        .order_by(StorePageVersion.created_at.desc(), StorePageVersion.id.desc())
        # _snapshot_version already prunes stored rows to MAX_VERSIONS_PER_PAGE,
        # but that's a separate write-path guarantee — this LIMIT makes the read
        # path safe on its own, independent of the pruning logic staying correct.
        .limit(MAX_VERSIONS_PER_PAGE)
    )
    versions = result.scalars().all()
    return [
        StorePageVersionSummary(
            id=v.id, created_at=v.created_at, title=v.title, section_count=len(v.sections or [])
        )
        for v in versions
    ]


async def revert_page_to_version_service(
    tenant_slug: str, page_key: str, page_type: str, version_id: int, db: AsyncSession
) -> StorePageSchema:
    tenant_id = await _get_tenant_id(tenant_slug, db)

    page_result = await db.execute(
        select(StorePage).where(
            StorePage.tenant_id == tenant_id, StorePage.page_key == page_key, StorePage.page_type == page_type
        )
    )
    page = page_result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404, detail=f"No page found for page_key='{page_key}' page_type='{page_type}'"
        )

    version_result = await db.execute(
        select(StorePageVersion).where(
            StorePageVersion.id == version_id,
            StorePageVersion.tenant_id == tenant_id,
            StorePageVersion.store_page_id == page.id,
        )
    )
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # The current state becomes a new version too, so reverting is itself
    # reversible — a revert is just another edit from the history's perspective.
    await _snapshot_version(page, db)

    page.title = version.title
    page.sections = version.sections
    page.background_color = version.background_color
    page.text_color = version.text_color

    await db.commit()
    await db.refresh(page)
    return _to_schema(page)


async def list_page_targets_service(tenant_slug: str, db: AsyncSession) -> List[StorePageSummary]:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(select(StorePage).where(StorePage.tenant_id == tenant_id))
    pages = result.scalars().all()
    return [
        StorePageSummary(
            page_key=p.page_key, page_type=p.page_type, title=p.title, section_count=len(p.sections or [])
        )
        for p in pages
    ]


async def get_page_schema_service(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> StorePageSchema:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(StorePage).where(
            StorePage.tenant_id == tenant_id, StorePage.page_key == page_key, StorePage.page_type == page_type
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404, detail=f"No page found for page_key='{page_key}' page_type='{page_type}'"
        )
    return _to_schema(page)


async def get_published_page_schema_service(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> StorePageSchema:
    """
    The only page-read path the public storefront is wired to. Deliberately a
    separate function from get_page_schema_service (the draft/admin one) rather
    than a boolean flag on it — a caller can't accidentally pass the wrong flag
    and leak a draft; the public router can only ever import this one.
    """
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(StorePage).where(
            StorePage.tenant_id == tenant_id, StorePage.page_key == page_key, StorePage.page_type == page_type
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404, detail=f"No page found for page_key='{page_key}' page_type='{page_type}'"
        )
    return _to_published_schema(page)


async def _publish_page_no_commit(tenant_id: int, page_key: str, page_type: str, db: AsyncSession) -> StorePage:
    result = await db.execute(
        select(StorePage).where(
            StorePage.tenant_id == tenant_id, StorePage.page_key == page_key, StorePage.page_type == page_type
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(
            status_code=404, detail=f"No page found for page_key='{page_key}' page_type='{page_type}'"
        )

    page.published_sections = page.sections
    page.published_title = page.title
    page.published_background_color = page.background_color
    page.published_text_color = page.text_color
    # Server-side clock (func.now()), same source as updated_at/created_at —
    # keeps the has_unpublished_changes comparison meaningful even if the app
    # server's own clock disagrees with the DB server's.
    page.published_at = func.now()

    if page.page_key == "home":
        settings_result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        settings = settings_result.scalar_one_or_none()
        if settings and settings.draft_template_key is not None:
            settings.template_key = settings.draft_template_key

    return page


async def publish_page_service(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> StorePageSchema:
    """
    Explicit store-owner action — never invoked automatically by an AI tool call.
    Copies the current draft verbatim into the published snapshot the public
    storefront reads. Single-page counterpart to publish_pages_service below,
    which the human-confirmed apply-template flow uses instead so a multi-page
    publish commits atomically.
    """
    tenant_id = await _get_tenant_id(tenant_slug, db)
    page = await _publish_page_no_commit(tenant_id, page_key, page_type, db)
    await db.commit()
    await db.refresh(page)
    return _to_schema(page)


async def publish_pages_service(
    tenant_slug: str, pages: List[StorePageSchema], db: AsyncSession
) -> List[StorePageSchema]:
    """
    Publishes multiple pages in a single transaction — either all of them publish
    or none do. Used after apply_storefront_template_service (reached only through
    the human-confirmed pending-action flow or the explicit apply-template
    endpoint, never called by the AI directly) so a failure partway through
    can't leave the storefront with some pages published on the new template and
    others still on the old one.
    """
    tenant_id = await _get_tenant_id(tenant_slug, db)
    published = [await _publish_page_no_commit(tenant_id, p.page_key, p.page_type, db) for p in pages]
    await db.commit()
    for page in published:
        await db.refresh(page)
    return [_to_schema(page) for page in published]


async def upsert_page_sections_service(
    tenant_slug: str, page_key: str, page_type: str, sections: List[Dict[str, Any]], db: AsyncSession,
    title: str | None = None,
    background_color: str | None = None,
    text_color: str | None = None,
) -> StorePageSchema:
    if page_key in RESERVED_PAGE_KEYS:
        raise HTTPException(status_code=400, detail=f"'{page_key}' is a reserved page_key and cannot be used for a real page")

    tenant_id = await _get_tenant_id(tenant_slug, db)

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id).options(selectinload(Tenant.settings))
    )
    tenant = tenant_result.scalar_one()
    supported_langs = (
        tenant.settings.supported_languages if tenant.settings and tenant.settings.supported_languages else ["he"]
    )
    sanitized_sections = _sanitize_sections(sections, supported_langs)

    # Enforce Pydantic validation before committing so any hallucinated payload
    # that bypassed the basic sanitizer is caught as a ValidationError here,
    # returned to the AI for retry, rather than persisting and crashing reads.
    for sec in sanitized_sections:
        Section(**sec)

    result = await db.execute(
        select(StorePage).where(
            StorePage.tenant_id == tenant_id, StorePage.page_key == page_key, StorePage.page_type == page_type
        )
    )
    page = result.scalar_one_or_none()

    # background_color/text_color follow the same "only touch it if the caller
    # actually said something" rule as title: omitted means leave as-is, an
    # empty string means explicitly clear it back to the page's default.
    if page:
        # Snapshot what's about to be overwritten — a brand new page has no
        # prior state worth saving, so this only runs on edits to an existing one.
        await _snapshot_version(page, db)
        page.sections = sanitized_sections
        if title:
            page.title = title
        if background_color is not None:
            page.background_color = background_color or None
        if text_color is not None:
            page.text_color = text_color or None
    else:
        page = StorePage(
            tenant_id=tenant_id,
            page_key=page_key,
            page_type=page_type,
            title=title or page_key.replace("_", " ").replace("-", " ").title(),
            sections=sanitized_sections,
            background_color=(background_color or None) if background_color is not None else None,
            text_color=(text_color or None) if text_color is not None else None,
        )
        db.add(page)

    await db.commit()
    await db.refresh(page)
    return _to_schema(page)


async def list_storefront_templates_service() -> List[StorefrontTemplateMeta]:
    """Metadata only (key/name/tagline/swatch) — the full section content never leaves the
    server except through apply_storefront_template_service, which writes it straight into the
    tenant's own StorePage rows rather than exposing the raw template payload to the client."""
    return list_storefront_template_metas()


async def apply_storefront_template_service(tenant_slug: str, template_key: str, db: AsyncSession) -> List[StorePageSchema]:
    """
    Seeds (or overwrites) this tenant's home/about/contact draft pages from a premium template.
    Does NOT publish automatically. It updates the draft versions so they can be previewed in the layout editor.
    """
    template = get_storefront_template(template_key)
    if not template:
        raise HTTPException(status_code=404, detail=f"Unknown storefront template: {template_key}")

    tenant_id = await _get_tenant_id(tenant_slug, db)

    results: List[StorePageSchema] = []
    for page_key, page_content in template["pages"].items():
        draft = await upsert_page_sections_service(
            tenant_slug, page_key, "static_page", page_content["sections"], db,
            title=page_content.get("title"),
            background_color=page_content.get("background_color"),
            text_color=page_content.get("text_color"),
        )
        results.append(draft)

    settings_result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    settings = settings_result.scalar_one_or_none()
    if not settings:
        settings = TenantSettings(tenant_id=tenant_id)
        db.add(settings)
    settings.draft_template_key = template_key

    await db.commit()
    return results
