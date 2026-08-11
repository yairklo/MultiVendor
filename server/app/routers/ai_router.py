from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_tenant_admin
from app.models.user import User
from app.schemas.ai_schemas import (
    AIChatRequest, AIChatResponse, AIStatusResponse, ConversationResponse, PageType, PendingConfirmation,
    StorePageSchema, StorePageSummary, StorePageVersionSummary, ToolCallRecord
)
from app.services import ai_conversation_service, ai_pending_action_service, store_page_service
from app.services.ai_agent_service import is_gemini_configured, run_agent_turn

ai_router = APIRouter(prefix="/api/v1/admin/store/{tenant_slug}/ai", tags=["AI Layout & Product Assistant"])


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


@ai_router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="Send a Message to the AI Layout/Product Assistant",
    description=(
        "Runs one turn of the AI tool-calling loop, scoped strictly to the authenticated vendor's own store. "
        "The AI can inspect/edit the given page's sections or create a new product using the same validation "
        "and subscription-limit checks as the manual admin flows."
    ),
)
async def post_ai_chat(
    req: AIChatRequest,
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await run_agent_turn(db, tenant_slug, req.message, req.page_key, req.page_type)

    page = None
    try:
        page = await store_page_service.get_page_schema_service(tenant_slug, req.page_key, req.page_type, db)
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
    summary="Get the AI Chat History for a Page",
    description="Restores the visible chat transcript for this page — empty if nothing has been asked yet.",
)
async def get_conversation(
    page_key: str = Query(...),
    page_type: PageType = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    messages = await ai_conversation_service.get_conversation_messages_service(tenant_slug, page_key, page_type, db)
    return ConversationResponse(messages=messages)


@ai_router.delete(
    "/conversation",
    status_code=204,
    summary="Start a New Conversation",
    description="Clears this page's chat memory, both the visible transcript and the AI's own recollection of it.",
)
async def delete_conversation(
    page_key: str = Query(...),
    page_type: PageType = Query(...),
    tenant_slug: str = Path(...),
    admin: User = Depends(get_tenant_admin),
    db: AsyncSession = Depends(get_db),
):
    await ai_conversation_service.clear_conversation_service(tenant_slug, page_key, page_type, db)
    return None
