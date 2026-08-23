from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_current_tenant, get_tenant_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.ai_schemas import (
    AIChatResponse, AIStatusResponse, ApplyStorefrontTemplateResponse, ConversationResponse, PageType,
    PendingConfirmation, SavePageSectionsRequest, StorePageSchema, StorePageSummary, StorePageVersionSummary,
    StorefrontTemplateSummary, ToolCallRecord
)
from app.services import ai_conversation_service, ai_pending_action_service, store_page_service
from app.services.ai_agent_service import is_gemini_configured, run_agent_turn
from app.services.catalog_service import get_store_config_service
from app.services.import_service import parse_products_excel
from app.services.storage_service import save_image
from app.schemas.tenant_schemas import TenantSettingsSchema

_SPREADSHEET_EXTENSIONS = (".xlsx",)
_IMAGE_CONTENT_PREFIX = "image/"


async def _build_chat_attachment(file: Optional[UploadFile], tenant: Tenant) -> Optional[Dict[str, Any]]:
    if file is None or not file.filename:
        return None

    if (file.content_type or "").startswith(_IMAGE_CONTENT_PREFIX):
        raw = await file.read()
        await file.seek(0)  # save_image below re-reads the file from the start
        url = await save_image(file, tenant.id, subdir="chat")
        return {"kind": "image", "filename": file.filename, "url": url, "mime_type": file.content_type, "bytes": raw}

    if file.filename.lower().endswith(_SPREADSHEET_EXTENSIONS):
        raw = await file.read()
        parsed = parse_products_excel(raw)
        return {"kind": "spreadsheet", "filename": file.filename, "parsed": parsed}

    raise HTTPException(status_code=400, detail="Unsupported file type -- attach an image or an .xlsx spreadsheet")

ai_router = APIRouter(
    prefix="/api/v1/admin/store/{tenant_slug}/ai",
    tags=["AI Layout & Product Assistant"],
    dependencies=[Depends(get_current_tenant)],
)


def _require_both_or_neither(page_key: Optional[str], page_type: Optional[str]) -> None:
    if (page_key is None) != (page_type is None):
        raise HTTPException(status_code=400, detail="page_key and page_type must both be provided or both omitted")


@ai_router.get(
    "/status",
    response_model=AIStatusResponse,
    summary="Get AI Assistant Status",
    description="Reports which provider is currently backing the AI assistant (live Gemini vs. offline mock mode).",
)
async def get_ai_status(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
):
    return AIStatusResponse(provider="gemini" if is_gemini_configured() else "mock")


@ai_router.get(
    "/config",
    response_model=TenantSettingsSchema,
    summary="Get Admin Store Configuration (Drafts Included)",
)
async def get_admin_store_config(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_store_config_service(tenant_slug, db, admin_preview=True)


@ai_router.get(
    "/page-targets",
    response_model=list[StorePageSummary],
    summary="List Editable Pages/Templates",
)
async def get_page_targets(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await store_page_service.list_page_targets_service(tenant_slug, db)


@ai_router.get(
    "/page-schema",
    response_model=StorePageSchema,
    summary="Get Page Section Schema",
)
async def get_page_schema(
    page_key: str = Query(...),
    page_type: PageType = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await store_page_service.get_page_schema_service(tenant_slug, page_key, page_type, db)


@ai_router.put(
    "/page-schema",
    response_model=StorePageSchema,
    summary="Manually Save a Page's Section Tree",
    description=(
        "Direct write path for drag-and-drop reordering in the admin editor — bypasses the AI tool-calling loop "
        "entirely, but reuses the identical recursive sanitizer, so a manually-dragged payload is validated "
        "exactly like an AI-authored one. Writes only to the draft — publishing still requires POST /publish."
    ),
)
async def put_page_schema(
    req: SavePageSectionsRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await store_page_service.upsert_page_sections_service(
        tenant_slug, req.page_key, req.page_type,
        [s.model_dump(exclude_none=True) for s in req.sections], db,
        title=req.title, background_color=req.background_color, text_color=req.text_color,
    )


def _parse_page_type(raw_type: Any) -> Optional[PageType]:
    if raw_type in (None, ""):
        return None
    if raw_type not in ("static_page", "template"):
        raise HTTPException(status_code=422, detail="Invalid page_type")
    return raw_type


async def _parse_chat_turn(request: Request) -> Tuple[str, Optional[str], Optional[PageType], Optional[UploadFile]]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=422, detail="Invalid chat payload")
        message = body.get("message")
        if message is None or not isinstance(message, str):
            raise HTTPException(status_code=422, detail="message is required")
        if len(message) > 4000:
            raise HTTPException(status_code=422, detail="message is too long")
        return message, body.get("page_key"), _parse_page_type(body.get("page_type")), None

    form = await request.form()
    message = form.get("message")
    if message is None or not isinstance(message, str):
        raise HTTPException(status_code=422, detail="message is required")
    uploaded = form.get("file")
    file = uploaded if isinstance(uploaded, UploadFile) else None
    page_key = form.get("page_key")
    return message, str(page_key) if page_key else None, _parse_page_type(form.get("page_type")), file


@ai_router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="Send a Message to the AI Layout/Product Assistant",
    description=(
        "Runs one turn of the AI tool-calling loop, scoped strictly to the authenticated vendor's own store. "
        "The AI can inspect/edit the given page's sections or create a new product using the same validation "
        "and subscription-limit checks as the manual admin flows. Accepts multipart/form-data so an image or "
        ".xlsx spreadsheet can optionally be attached alongside the message -- the agent can see the image or "
        "act on the parsed spreadsheet rows (e.g. via bulk_import_products)."
    ),
)
async def post_ai_chat(
    request: Request,
    tenant_slug: str = Path(...),
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    message, page_key, page_type, file = await _parse_chat_turn(request)
    _require_both_or_neither(page_key, page_type)
    attachment = await _build_chat_attachment(file, tenant)
    result = await run_agent_turn(db, tenant_slug, message, page_key, page_type, attachment=attachment)

    page = None
    if page_key is not None:
        try:
            page = await store_page_service.get_page_schema_service(tenant_slug, page_key, page_type, db)
        except HTTPException:
            pass

    pending = result.get("pending_confirmation")
    return AIChatResponse(
        reply=result["reply"],
        tool_calls=[ToolCallRecord(**tc) for tc in result["tool_calls"]],
        used_provider=result["used_provider"],
        page=page,
        pending_confirmation=PendingConfirmation(**pending) if pending else None,
    )


@ai_router.post(
    "/pending-actions/{confirmation_id}/confirm",
    summary="Confirm a Staged Destructive Action",
    description=(
        "The only path that actually performs delete_product or an order cancellation the AI staged — reached "
        "solely by an explicit human click, gated by the exact same tenant-admin auth as every other action here."
    ),
)
async def post_confirm_pending_action(
    confirmation_id: str = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ai_pending_action_service.confirm_pending_action_service(tenant_slug, confirmation_id, db)


@ai_router.post(
    "/pending-actions/{confirmation_id}/cancel",
    status_code=204,
    summary="Cancel a Staged Destructive Action",
    description="Discards a staged delete_product/cancel-order action without executing anything.",
)
async def post_cancel_pending_action(
    confirmation_id: str = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    await ai_pending_action_service.cancel_pending_action_service(tenant_slug, confirmation_id, db)
    return None


@ai_router.post(
    "/publish",
    response_model=StorePageSchema,
    summary="Publish the Current Draft to the Live Storefront",
    description=(
        "Copies the current draft (whatever the AI/admin preview currently shows) to the published snapshot "
        "the public storefront reads. This is the ONLY way a change ever reaches real shoppers — AI edits and "
        "admin preview changes only ever touch the draft. Never called automatically; it's an explicit "
        "store-owner action."
    ),
)
async def post_publish_page(
    page_key: str = Query(...),
    page_type: PageType = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await store_page_service.publish_page_service(tenant_slug, page_key, page_type, db)


@ai_router.get(
    "/page-versions",
    response_model=list[StorePageVersionSummary],
    summary="List a Page's Version History",
    description="Snapshots are taken automatically on every edit to an existing page — this lists them, newest first.",
)
async def get_page_versions(
    page_key: str = Query(...),
    page_type: PageType = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await store_page_service.list_page_versions_service(tenant_slug, page_key, page_type, db)


@ai_router.post(
    "/page-versions/{version_id}/revert",
    response_model=StorePageSchema,
    summary="Revert a Page to a Prior Version",
    description="Restores the page to a previous snapshot. The current state is itself saved as a new version first, so this can be undone too.",
)
async def post_revert_page_version(
    version_id: int = Path(...),
    page_key: str = Query(...),
    page_type: PageType = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    return await store_page_service.revert_page_to_version_service(tenant_slug, page_key, page_type, version_id, db)


@ai_router.get(
    "/conversation",
    response_model=ConversationResponse,
    summary="Get the AI Chat History for a Page (or the Global Copilot)",
    description=(
        "Restores the visible chat transcript — for a specific page's conversation if page_key/page_type are "
        "given, or the tenant-wide global copilot conversation if both are omitted. Empty if nothing's been "
        "asked yet."
    ),
)
async def get_conversation(
    page_key: Optional[str] = Query(default=None),
    page_type: Optional[PageType] = Query(default=None),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    _require_both_or_neither(page_key, page_type)
    messages = await ai_conversation_service.get_conversation_messages_service(tenant_slug, page_key, page_type, db)
    return ConversationResponse(messages=messages)


@ai_router.get(
    "/templates",
    response_model=list[StorefrontTemplateSummary],
    summary="List Premium Storefront Templates",
    description="Lists the 3 selectable storefront templates (name/tagline/color swatch) a seller can apply.",
)
async def get_storefront_templates(
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
):
    return await store_page_service.list_storefront_templates_service()


@ai_router.post(
    "/templates/{template_key}/apply",
    response_model=ApplyStorefrontTemplateResponse,
    summary="Apply a Premium Storefront Template",
    description=(
        "Seeds (overwriting) this store's home/about/contact pages from the chosen template and publishes them "
        "immediately, so the storefront reflects the new template right away. Every edit made after this still "
        "goes through the normal draft -> explicit Publish flow."
    ),
)
async def post_apply_storefront_template(
    template_key: str = Path(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    pages = await store_page_service.apply_storefront_template_service(tenant_slug, template_key, db)
    published_pages = await store_page_service.publish_pages_service(tenant_slug, pages, db)
    return ApplyStorefrontTemplateResponse(template_key=template_key, pages=published_pages)


@ai_router.delete(
    "/conversation",
    status_code=204,
    summary="Start a New Conversation",
    description=(
        "Clears the chat memory — for a specific page if page_key/page_type are given, or the tenant-wide "
        "global copilot conversation if both are omitted — both the visible transcript and the AI's own "
        "recollection of it."
    ),
)
async def delete_conversation(
    page_key: Optional[str] = Query(default=None),
    page_type: Optional[PageType] = Query(default=None),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    _require_both_or_neither(page_key, page_type)
    await ai_conversation_service.clear_conversation_service(tenant_slug, page_key, page_type, db)
    return None
