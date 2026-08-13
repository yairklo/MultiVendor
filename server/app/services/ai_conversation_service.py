from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.store_page import AIConversation
from app.schemas.ai_schemas import ChatMessageRecord

MAX_STORED_MESSAGES = 40


async def _get_tenant_id(tenant_slug: str, db: AsyncSession) -> int:
    result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


def _conversation_filter(tenant_id: int, page_key: Optional[str], page_type: Optional[str]):
    """
    page_key/page_type both None identifies the single tenant-wide global copilot
    conversation, not tied to any real page — never a fake page_key like 'global'.
    `Column == None` compiles to `IS NULL` (SQLAlchemy special-cases this), so this
    already produces `page_key IS NULL AND page_type IS NULL` for the global case —
    exactly the row the DB's uq_ai_conversations_tenant_key_type index (over
    COALESCE'd generated columns, since MySQL treats every NULL as distinct)
    enforces at most one of per tenant.
    """
    return (
        AIConversation.tenant_id == tenant_id,
        AIConversation.page_key == page_key,
        AIConversation.page_type == page_type,
    )


async def _load_conversation(
    tenant_slug: str, page_key: Optional[str], page_type: Optional[str], db: AsyncSession
) -> Optional[AIConversation]:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(select(AIConversation).where(*_conversation_filter(tenant_id, page_key, page_type)))
    return result.scalar_one_or_none()


async def get_conversation_messages_service(
    tenant_slug: str, page_key: Optional[str], page_type: Optional[str], db: AsyncSession
) -> List[ChatMessageRecord]:
    convo = await _load_conversation(tenant_slug, page_key, page_type, db)
    if not convo:
        return []
    return [ChatMessageRecord(**m) for m in (convo.messages or [])]


async def load_gemini_history_json(
    tenant_slug: str, page_key: Optional[str], page_type: Optional[str], db: AsyncSession
) -> Optional[List[Dict[str, Any]]]:
    """
    Raw serialized google.genai Content[] for this tenant's page (or the global
    copilot conversation, if page_key/page_type are None), or None if there's no
    conversation yet. Deserializing into real Content objects is
    ai_agent_service's job — this module stays provider-agnostic.
    """
    convo = await _load_conversation(tenant_slug, page_key, page_type, db)
    return convo.gemini_history if convo else None


async def save_conversation_turn(
    tenant_slug: str,
    page_key: Optional[str],
    page_type: Optional[str],
    new_messages: List[Dict[str, Any]],
    db: AsyncSession,
    gemini_history_json: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Appends `new_messages` (plain dicts matching ChatMessageRecord) to this
    tenant+page's stored transcript (or the tenant's global copilot transcript,
    if page_key/page_type are None), and — only when the caller actually has a
    fresh one (i.e. a real Gemini turn just ran) — replaces gemini_history_json
    with the latest full history. tenant_id is resolved here, from tenant_slug,
    exactly like every other write in this feature; a conversation can never be
    saved against, or read back from, any tenant other than the one making the
    request.
    """
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(select(AIConversation).where(*_conversation_filter(tenant_id, page_key, page_type)))
    convo = result.scalar_one_or_none()

    if convo:
        merged_messages = [*(convo.messages or []), *new_messages][-MAX_STORED_MESSAGES:]
        convo.messages = merged_messages
        if gemini_history_json is not None:
            convo.gemini_history = gemini_history_json
        await db.commit()
        return

    db.add(AIConversation(
        tenant_id=tenant_id,
        page_key=page_key,
        page_type=page_type,
        gemini_history=gemini_history_json,
        messages=new_messages[-MAX_STORED_MESSAGES:],
    ))
    try:
        await db.commit()
    except IntegrityError:
        # Lost a race against a concurrent first message to the same (tenant,
        # page_key, page_type) — most likely two tabs both opening the global
        # copilot at once. The DB's unique index (which treats NULL/NULL
        # consistently via generated columns) is what actually catches this;
        # fall back to merging into the row the other request just created
        # instead of surfacing a 500 for what's really just a normal append.
        await db.rollback()
        result = await db.execute(select(AIConversation).where(*_conversation_filter(tenant_id, page_key, page_type)))
        convo = result.scalar_one()
        merged_messages = [*(convo.messages or []), *new_messages][-MAX_STORED_MESSAGES:]
        convo.messages = merged_messages
        if gemini_history_json is not None:
            convo.gemini_history = gemini_history_json
        await db.commit()


async def clear_conversation_service(
    tenant_slug: str, page_key: Optional[str], page_type: Optional[str], db: AsyncSession
) -> None:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    await db.execute(delete(AIConversation).where(*_conversation_filter(tenant_id, page_key, page_type)))
    await db.commit()
