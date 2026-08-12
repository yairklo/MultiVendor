import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.ai_pending_action import AIPendingAction
from app.schemas.ai_schemas import PendingConfirmation
from app.services import catalog_service, order_service, store_page_service

PENDING_ACTION_TTL_MINUTES = 15

# Tools that never execute directly — create_pending_action_service stages them
# instead, and only confirm_pending_action_service (triggered by a real button
# click, never the AI itself) actually runs the underlying service call.
GATED_TOOLS = ("delete_product", "update_order_status", "apply_storefront_template")


async def _get_tenant_id(tenant_slug: str, db: AsyncSession) -> int:
    result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


async def create_pending_action_service(
    tenant_slug: str, tool_name: str, tool_args: Dict[str, Any], summary: str, db: AsyncSession
) -> PendingConfirmation:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    action = AIPendingAction(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        tool_name=tool_name,
        tool_args=tool_args,
        summary=summary,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=PENDING_ACTION_TTL_MINUTES),
    )
    db.add(action)
    await db.commit()
    return PendingConfirmation(id=action.id, tool_name=tool_name, summary=summary)


async def _load_pending_action(tenant_slug: str, confirmation_id: str, db: AsyncSession) -> AIPendingAction:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(AIPendingAction).where(
            AIPendingAction.id == confirmation_id, AIPendingAction.tenant_id == tenant_id
        )
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Pending action not found")
    if action.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        await db.delete(action)
        await db.commit()
        raise HTTPException(status_code=410, detail="This confirmation has expired — ask the AI again")
    return action


async def confirm_pending_action_service(tenant_slug: str, confirmation_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    The only path that actually performs a gated action — reached solely by an
    explicit UI button click, authenticated by the same Depends(get_tenant_admin)
    every other admin action requires. Re-resolves tenant_slug -> tenant_id itself
    (via the underlying service calls) rather than trusting anything stored on the
    pending row beyond the id, so this can never act outside the confirming
    tenant's own store even if the row were somehow tampered with.
    """
    action = await _load_pending_action(tenant_slug, confirmation_id, db)
    args = action.tool_args

    try:
        if action.tool_name == "delete_product":
            await catalog_service.delete_product_service(tenant_slug, args["product_id"], db)
            result = {"status": "ok", "product_id": args["product_id"], "deleted": True}
        elif action.tool_name == "update_order_status":
            result = await order_service.update_order_status_service(tenant_slug, args["order_id"], args["status"], db)
        elif action.tool_name == "apply_storefront_template":
            # Seeds the draft pages then publishes them all in one transaction
            # (publish_pages_service), so a failure partway through can't leave
            # the storefront half-migrated to the new template.
            pages = await store_page_service.apply_storefront_template_service(tenant_slug, args["template_key"], db)
            published_pages = await store_page_service.publish_pages_service(tenant_slug, pages, db)
            result = {"status": "ok", "template_key": args["template_key"], "pages": [p.model_dump(mode="json") for p in published_pages]}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown pending action tool: {action.tool_name}")
            
        await db.delete(action)
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise e




async def cancel_pending_action_service(tenant_slug: str, confirmation_id: str, db: AsyncSession) -> None:
    action = await _load_pending_action(tenant_slug, confirmation_id, db)
    await db.delete(action)
    await db.commit()
