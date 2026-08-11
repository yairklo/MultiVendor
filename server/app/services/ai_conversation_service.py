from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import delete, select
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


async def _load_conversation(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> Optional[AIConversation]:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.tenant_id == tenant_id,
            AIConversation.page_key == page_key,
            AIConversation.page_type == page_type,
        )
    )
    return result.scalar_one_or_none()


async def get_conversation_messages_service(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> List[ChatMessageRecord]:
    convo = await _load_conversation(tenant_slug, page_key, page_type, db)
    if not convo:
        return []
    return [ChatMessageRecord(**m) for m in (convo.messages or [])]


async def load_gemini_history_json(
    tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> Optional[List[Dict[str, Any]]]:
    """
    Raw serialized google.genai Content[] for this tenant's page, or None if
    there's no conversation yet. Deserializing into real Content objects is
    ai_agent_service's job — this module stays provider-agnostic.
    """
    convo = await _load_conversation(tenant_slug, page_key, page_type, db)
    return convo.gemini_history if convo else None


async def save_conversation_turn(
    tenant_slug: str,
    page_key: str,
    page_type: str,
    new_messages: List[Dict[str, Any]],
    db: AsyncSession,
    gemini_history_json: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    Appends `new_messages` (plain dicts matching ChatMessageRecord) to this
    tenant+page's stored transcript, and — only when the caller actually has a
    fresh one (i.e. a real Gemini turn just ran) — replaces gemini_history_json
    with the latest full history. tenant_id is resolved here, from tenant_slug,
    exactly like every other write in this feature; a conversation can never be
    saved against, or read back from, any tenant other than the one making the
    request.
    """
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.tenant_id == tenant_id,
            AIConversation.page_key == page_key,
            AIConversation.page_type == page_type,
        )
    )
    convo = result.scalar_one_or_none()

    if convo:
        merged_messages = [*(convo.messages or []), *new_messages][-MAX_STORED_MESSAGES:]
        convo.messages = merged_messages
        if gemini_history_json is not None:
            convo.gemini_history = gemini_history_json
    else:
        db.add(AIConversation(
            tenant_id=tenant_id,
            page_key=page_key,
            page_type=page_type,
            gemini_history=gemini_history_json,
            messages=new_messages[-MAX_STORED_MESSAGES:],
        ))

    await db.commit()


async def clear_conversation_service(tenant_slug: str, page_key: str, page_type: str, db: AsyncSession) -> None:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    await db.execute(
        delete(AIConversation).where(
            AIConversation.tenant_id == tenant_id,
            AIConversation.page_key == page_key,
            AIConversation.page_type == page_type,
        )
    )
    await db.commit()
