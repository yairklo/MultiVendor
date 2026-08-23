"""
Coverage for the AI copilot page-scope redesign: page_key/page_type became
genuinely optional (None/None = the tenant-wide global copilot conversation)
instead of the frontend faking page_key='global' to satisfy a schema built
only for the per-page layout editor. See tests/test_ai_layout.py for the
real-page-scoped behavior this deliberately leaves unchanged.
"""
import asyncio

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.store_page import AIConversation, StorePage
from app.models.tenant import Tenant
from app.services import ai_conversation_service, ai_mock_agent
from app.services.ai_agent_service import (
    _NO_PAGE_CONTEXT_INSTRUCTION,
    _PAGE_CONTEXT_INSTRUCTION,
    _build_system_instruction,
)
from app.services.ai_mock_agent import run_mock_agent
from app.services.ai_tool_executor import execute_tool
from app.services.store_page_service import RESERVED_PAGE_KEYS, upsert_page_sections_service


async def _tenant_id(db_session, slug="tenant-a") -> int:
    return (await db_session.execute(select(Tenant.id).where(Tenant.slug == slug))).scalar_one()


# ---------------------------------------------------------------------------
# AIChatRequest / conversation query params: optional, but only together
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat_endpoint_accepts_a_message_with_no_page_context(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "how many orders came in this week"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    # No real page was ever specified, so there's nothing to echo back.
    assert body["page"] is None


@pytest.mark.asyncio
async def test_chat_endpoint_rejects_half_specified_page_context(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "hi", "page_key": "home"},  # page_type omitted
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_conversation_endpoints_accept_no_page_context(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    get_resp = await async_client.get("/api/v1/admin/store/tenant-a/ai/conversation", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["messages"] == []

    delete_resp = await async_client.delete("/api/v1/admin/store/tenant-a/ai/conversation", headers=headers)
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_conversation_endpoints_reject_half_specified_page_context(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    get_resp = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_type=static_page", headers=headers
    )
    assert get_resp.status_code == 400

    delete_resp = await async_client.delete(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_key=home", headers=headers
    )
    assert delete_resp.status_code == 400


# ---------------------------------------------------------------------------
# The global conversation is a distinct thread, not aliased to any real page
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_global_conversation_is_isolated_from_a_real_pages_conversation(
    async_client: AsyncClient, seed_tokens
):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}

    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner", "page_key": "home", "page_type": "static_page"},
        headers=headers,
    )
    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat", json={"message": "how many orders this week"}, headers=headers
    )

    page_convo = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_key=home&page_type=static_page", headers=headers
    )
    global_convo = await async_client.get("/api/v1/admin/store/tenant-a/ai/conversation", headers=headers)

    assert page_convo.json()["messages"][0]["text"] == "add a hero banner"
    assert len(page_convo.json()["messages"]) == 2  # just its own user/assistant pair
    assert len(global_convo.json()["messages"]) == 2  # just its own user/assistant pair
    assert global_convo.json()["messages"][0]["text"] == "how many orders this week"

    # Clearing the global thread must not touch the page's own history.
    await async_client.delete("/api/v1/admin/store/tenant-a/ai/conversation", headers=headers)
    global_after_clear = await async_client.get("/api/v1/admin/store/tenant-a/ai/conversation", headers=headers)
    page_after_clear = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_key=home&page_type=static_page", headers=headers
    )
    assert global_after_clear.json()["messages"] == []
    assert len(page_after_clear.json()["messages"]) == 2


@pytest.mark.asyncio
async def test_global_conversation_never_leaks_between_tenants(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}

    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat", json={"message": "tenant a's global message"}, headers=headers_a
    )

    convo_b = await async_client.get("/api/v1/admin/store/tenant-b/ai/conversation", headers=headers_b)
    assert convo_b.json()["messages"] == []


# ---------------------------------------------------------------------------
# Offline mock agent: no page open means no layout-editing fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_agent_declines_layout_edit_without_a_page_open(db_session):
    result = await run_mock_agent("please add a banner to my homepage", "tenant-a", None, None, db_session)
    assert result["reply"] == ai_mock_agent._NO_PAGE_FALLBACK_REPLY
    # Crucially, it must never have attempted get_page_schema/update_page_sections
    # against a fake page_key — no tool call at all for this input.
    assert result["tool_calls"] == []

    # And, unlike the pre-fix behavior, nothing gets silently created.
    tenant_id = await _tenant_id(db_session)
    stray = (await db_session.execute(
        select(StorePage).where(StorePage.tenant_id == tenant_id, StorePage.page_key == "global")
    )).scalar_one_or_none()
    assert stray is None


@pytest.mark.asyncio
async def test_mock_agent_store_management_commands_work_without_a_page_open(db_session):
    result = await run_mock_agent("show low stock", "tenant-a", None, None, db_session)
    assert result["reply"] != ai_mock_agent._NO_PAGE_FALLBACK_REPLY
    assert result["tool_calls"][0]["name"] == "get_inventory_health"

    result = await run_mock_agent("create a coupon SAVE10 for 10% off", "tenant-a", None, None, db_session)
    assert result["tool_calls"][0]["name"] == "create_coupon"
    assert result["tool_calls"][0]["is_error"] is False


# ---------------------------------------------------------------------------
# System prompt: no false "you are editing page_key=X" premise without a page
# ---------------------------------------------------------------------------

def test_system_instruction_without_page_context_has_no_fake_page():
    instruction = _build_system_instruction(None, None)
    assert _NO_PAGE_CONTEXT_INSTRUCTION in instruction
    # 'global' legitimately appears once, naming it as the forbidden placeholder
    # to guard against — never as if it were a real, currently-open page.
    assert 'page_key="global"' not in instruction
    assert 'page_key="None"' not in instruction
    assert "currently editing" not in instruction


def test_system_instruction_with_page_context_is_unchanged():
    instruction = _build_system_instruction("home", "static_page")
    assert _PAGE_CONTEXT_INSTRUCTION.format(page_key="home", page_type="static_page") in instruction
    assert _NO_PAGE_CONTEXT_INSTRUCTION not in instruction


@pytest.mark.asyncio
async def test_run_agent_turn_with_no_page_context_sends_the_no_page_prompt_to_gemini(db_session, monkeypatch):
    import google.genai as genai
    from google.genai import types
    from app.services import ai_agent_service

    captured_config = {}

    class _FakeResponse:
        function_calls = []
        text = "You have 3 orders this week."

    class _FakeChat:
        def get_history(self):
            return []

        async def send_message(self, _parts):
            return _FakeResponse()

    class _FakeChats:
        def create(self, model, config, history=None):
            captured_config["system_instruction"] = config.system_instruction
            return _FakeChat()

    class _FakeClient:
        def __init__(self, api_key=None):
            self.aio = type("Aio", (), {"chats": _FakeChats()})()

    monkeypatch.setattr(genai, "Client", _FakeClient)
    monkeypatch.setattr(ai_agent_service.settings, "GEMINI_API_KEY", "test-fake-key")

    result = await ai_agent_service.run_agent_turn(db_session, "tenant-a", "how many orders this week", None, None)

    assert result["used_provider"] == "gemini"
    assert 'page_key="global"' not in captured_config["system_instruction"]
    assert _NO_PAGE_CONTEXT_INSTRUCTION in captured_config["system_instruction"]

    # And it persisted under the global (None, None) thread, not a fake page.
    stored = await ai_conversation_service.get_conversation_messages_service("tenant-a", None, None, db_session)
    assert stored[0].text == "how many orders this week"


# ---------------------------------------------------------------------------
# 'global' is reserved — a page-layout tool call can never create that page
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_page_sections_service_rejects_the_reserved_global_page_key(db_session):
    assert "global" in RESERVED_PAGE_KEYS
    with pytest.raises(HTTPException) as exc_info:
        await upsert_page_sections_service("tenant-a", "global", "static_page", [], db_session)
    assert exc_info.value.status_code == 400

    tenant_id = await _tenant_id(db_session)
    stray = (await db_session.execute(
        select(StorePage).where(StorePage.tenant_id == tenant_id, StorePage.page_key == "global")
    )).scalar_one_or_none()
    assert stray is None


@pytest.mark.asyncio
async def test_update_page_sections_tool_rejects_the_reserved_global_page_key(db_session):
    result = await execute_tool(
        "update_page_sections",
        {"page_key": "global", "page_type": "static_page", "sections": []},
        "tenant-a",
        db_session,
    )
    assert result.is_error is True
    assert "reserved" in result.output["error"].lower()


# ---------------------------------------------------------------------------
# Duplicate-global-row protection: MySQL treats every NULL as distinct, so a
# plain UNIQUE(tenant_id, page_key, page_type) would NOT stop two concurrent
# first messages from each inserting their own (tenant_id, NULL, NULL) row —
# these tests cover both the DB-level index and the app-level upsert fallback.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_db_unique_index_rejects_a_second_null_null_conversation_row(db_session):
    tenant_id = await _tenant_id(db_session)
    db_session.add(AIConversation(tenant_id=tenant_id, page_key=None, page_type=None, messages=[]))
    await db_session.commit()

    db_session.add(AIConversation(tenant_id=tenant_id, page_key=None, page_type=None, messages=[]))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_concurrent_first_global_messages_merge_instead_of_duplicating(db_session, monkeypatch):
    from conftest import AsyncSessionLocal

    tenant_id = await _tenant_id(db_session)
    original_execute = db_session.execute
    calls = {"n": 0}

    async def racy_execute(stmt, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            # Simulate a concurrent request winning the race right after our own
            # SELECT found nothing, but before our INSERT commits: create the
            # competing row through a fully independent session/connection.
            async with AsyncSessionLocal() as other_session:
                other_session.add(AIConversation(
                    tenant_id=tenant_id, page_key=None, page_type=None,
                    messages=[{"role": "user", "text": "from the other request"}],
                ))
                await other_session.commit()
        return await original_execute(stmt, *args, **kwargs)

    monkeypatch.setattr(db_session, "execute", racy_execute)

    await ai_conversation_service.save_conversation_turn(
        "tenant-a", None, None, [{"role": "user", "text": "from us"}], db_session
    )

    rows = (await db_session.execute(
        select(AIConversation).where(
            AIConversation.tenant_id == tenant_id, AIConversation.page_key.is_(None), AIConversation.page_type.is_(None)
        )
    )).scalars().all()
    assert len(rows) == 1
    texts = [m["text"] for m in rows[0].messages]
    assert "from the other request" in texts
    assert "from us" in texts
