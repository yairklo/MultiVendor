import secrets
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.store_page import StorePage, StorePageVersion
from app.schemas.ai_schemas import (
    StorePageSchema, StorePageSummary, StorePageVersionSummary, Section,
    SECTION_TYPES, BUTTON_ACTION_TYPES, BUTTON_VARIANTS, CONTAINER_SECTION_TYPES,
    DESIGN_VARIANTS, MAX_SECTION_NESTING_DEPTH,
)

MAX_VERSIONS_PER_PAGE = 20


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


def _sanitize_button_group_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    button_group is the one section type that drives runtime behavior (a click
    dispatches actionType/actionPayload), so unlike other settings we don't just
    pass it through — any button with an actionType outside the fixed allow-list
    is dropped before it's ever persisted, so the AI can never smuggle an
    unrecognized action through to the frontend.
    """
    buttons = settings.get("buttons")
    buttons = buttons if isinstance(buttons, list) else []
    sanitized = []
    for b in buttons:
        if not isinstance(b, dict):
            continue
        if not isinstance(b.get("label"), str) or b.get("actionType") not in BUTTON_ACTION_TYPES:
            continue
        entry = {
            "label": b["label"],
            "variant": b.get("variant") if b.get("variant") in BUTTON_VARIANTS else "primary",
            "actionType": b["actionType"],
        }
        if isinstance(b.get("actionPayload"), dict):
            entry["actionPayload"] = b["actionPayload"]
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


def _sanitize_sections(
    raw_sections: List[Dict[str, Any]], seen_ids: "set | None" = None, depth: int = 0
) -> List[Dict[str, Any]]:
    # A single seen_ids set is threaded through every recursive call (never recreated per
    # call) so generated ids stay globally unique across nesting levels, not just within one.
    if seen_ids is None:
        seen_ids = set()
    if depth > MAX_SECTION_NESTING_DEPTH:
        raise HTTPException(status_code=400, detail="Section nesting too deep")

    sanitized: List[Dict[str, Any]] = []
    for raw in raw_sections:
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

        entry: Dict[str, Any] = {"id": section_id, "type": section_type, "settings": settings}
        if raw.get("media"):
            entry["media"] = raw["media"]

        if section_type == "grid_container":
            children = raw.get("children") if isinstance(raw.get("children"), list) else []
            entry["children"] = _sanitize_sections(children, seen_ids, depth + 1)
        elif section_type == "two_column_layout":
            zones_raw = raw.get("zones") if isinstance(raw.get("zones"), dict) else {}
            entry["zones"] = {
                zone: _sanitize_sections(items, seen_ids, depth + 1)
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


async def publish_page_service(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> StorePageSchema:
    """
    Explicit store-owner action — never called by the AI or any tool. Copies the
    current draft verbatim into the published snapshot the public storefront reads.
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

    page.published_sections = page.sections
    page.published_title = page.title
    page.published_background_color = page.background_color
    page.published_text_color = page.text_color
    # Server-side clock (func.now()), same source as updated_at/created_at —
    # keeps the has_unpublished_changes comparison meaningful even if the app
    # server's own clock disagrees with the DB server's.
    page.published_at = func.now()

    await db.commit()
    await db.refresh(page)
    return _to_schema(page)


async def upsert_page_sections_service(
    tenant_slug: str, page_key: str, page_type: str, sections: List[Dict[str, Any]], db: AsyncSession,
    title: str | None = None,
    background_color: str | None = None,
    text_color: str | None = None,
) -> StorePageSchema:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    sanitized_sections = _sanitize_sections(sections)

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
