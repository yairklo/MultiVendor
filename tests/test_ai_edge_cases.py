"""
Adversarial / edge-case regression suite for the AI copilot: ambiguous,
oversized, spam/gibberish, and dangerous-content input. Every test here uses
either the scripted-fake Gemini harness (same self-contained pattern as
tests/test_ai_guardrails.py — zero network calls, real google.genai.types
objects) or a plain unit/service-level call — deliberately never a real
Gemini API call, per an explicit cost constraint from the project owner.
"""
import google.genai as genai
import pytest
from google.genai import types
from httpx import AsyncClient
from sqlalchemy import select

from app.models.store_page import StorePage
from app.models.tenant import Tenant
from app.services import ai_agent_service, ai_conversation_service, ai_pending_action_service
from app.services.ai_agent_service import _AMBIGUITY_INSTRUCTION, _build_system_instruction, _is_degenerate_input
from app.services.ai_tool_executor import execute_tool
from app.services.store_page_service import _sanitize_url, upsert_page_sections_service


# ---------------------------------------------------------------------------
# Scripted fake Gemini chat — duplicated locally rather than imported, same
# self-contained style tests/test_ai_guardrails.py already uses.
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, function_calls, text):
        self.function_calls = function_calls
        self.text = text


class _ScriptedChat:
    def __init__(self, script):
        self._script = list(script)
        self._history = []
        self.send_message_calls = []

    async def send_message(self, parts):
        self.send_message_calls.append(parts)
        incoming_parts = [types.Part(text=parts)] if isinstance(parts, str) else list(parts)
        self._history.append(types.Content(role="user", parts=incoming_parts))

        step = self._script.pop(0)
        if "call" in step:
            name, args = step["call"]
            fc = types.FunctionCall(name=name, args=args)
            self._history.append(types.Content(role="model", parts=[types.Part(function_call=fc)]))
            return _FakeResponse(function_calls=[fc], text=None)

        self._history.append(types.Content(role="model", parts=[types.Part(text=step["text"])]))
        return _FakeResponse(function_calls=[], text=step["text"])

    def get_history(self):
        return self._history


class _FakeChats:
    def __init__(self, chat):
        self._chat = chat

    def create(self, model, config, history=None):
        return self._chat


class _FakeClient:
    def __init__(self, chat):
        self.aio = type("Aio", (), {"chats": _FakeChats(chat)})()


def _patch_gemini(monkeypatch, script):
    chat = _ScriptedChat(script)
    monkeypatch.setattr(genai, "Client", lambda api_key=None: _FakeClient(chat))
    monkeypatch.setattr(ai_agent_service.settings, "GEMINI_API_KEY", "test-fake-key")
    return chat


def _forbid_gemini_client(monkeypatch):
    """Any attempt to construct a Gemini client fails the test loudly — used to
    prove a guard short-circuits BEFORE ever reaching (and paying for) the API."""
    def _boom(api_key=None):
        raise AssertionError("genai.Client() was called — the guard did not short-circuit before the API call")
    monkeypatch.setattr(genai, "Client", _boom)
    monkeypatch.setattr(ai_agent_service.settings, "GEMINI_API_KEY", "test-fake-key")


async def _tenant_id(db_session, slug="tenant-a") -> int:
    return (await db_session.execute(select(Tenant.id).where(Tenant.slug == slug))).scalar_one()


# ---------------------------------------------------------------------------
# Feature 2 — cost/abuse guard on the message itself
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_oversized_message_is_rejected_before_reaching_gemini(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "x" * 5000},
        headers=headers,
    )
    assert resp.status_code == 422


def test_is_degenerate_input_flags_repeated_character_and_pattern_spam():
    assert _is_degenerate_input("a" * 200) is True
    assert _is_degenerate_input("asdasdasdasdasdasdasdasdasdasd") is True
    assert _is_degenerate_input("                              ") is True
    assert _is_degenerate_input("") is True
    assert _is_degenerate_input("!!!!!!!!") is True


def test_is_degenerate_input_never_flags_real_short_or_multilingual_text():
    assert _is_degenerate_input("how many orders came in this week?") is False
    assert _is_degenerate_input("תוסיף באנר לדף הבית בבקשה") is False
    assert _is_degenerate_input("add a hero banner and move the gallery above the products") is False
    assert _is_degenerate_input("cancel it") is False
    assert _is_degenerate_input("ok") is False


@pytest.mark.asyncio
async def test_degenerate_input_short_circuits_without_ever_calling_gemini(db_session, monkeypatch):
    _forbid_gemini_client(monkeypatch)

    result = await ai_agent_service.run_agent_turn(db_session, "tenant-a", "aaaaaaaaaaaaaaaaaaaa", None, None)

    assert result["tool_calls"] == []
    assert result["reply"]  # a real, non-empty canned reply — not silently swallowed

    stored = await ai_conversation_service.get_conversation_messages_service("tenant-a", None, None, db_session)
    assert stored[0].text == "aaaaaaaaaaaaaaaaaaaa"
    assert stored[1].text == result["reply"]


# ---------------------------------------------------------------------------
# Feature 3 — URL-scheme allow-list for AI-authored content
# ---------------------------------------------------------------------------

def test_sanitize_url_allows_safe_schemes_and_relative_links():
    assert _sanitize_url("https://example.com/sale") == "https://example.com/sale"
    assert _sanitize_url("http://example.com") == "http://example.com"
    assert _sanitize_url("/shop") == "/shop"
    assert _sanitize_url("#reviews") == "#reviews"
    assert _sanitize_url("mailto:hello@store.com") == "mailto:hello@store.com"


def test_sanitize_url_strips_dangerous_schemes():
    assert _sanitize_url("javascript:alert(1)") is None
    assert _sanitize_url("data:text/html,<script>alert(1)</script>") is None
    assert _sanitize_url("vbscript:msgbox(1)") is None
    assert _sanitize_url(None) is None
    assert _sanitize_url("") is None


@pytest.mark.asyncio
async def test_update_page_sections_drops_javascript_href_from_button_actionpayload(db_session):
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "xss-button-test",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [
                            {
                                "label": "Malicious",
                                "actionType": "NAVIGATE",
                                "actionPayload": {"href": "javascript:alert(document.cookie)"},
                            },
                            {"label": "Legit", "actionType": "NAVIGATE", "actionPayload": {"href": "/shop"}},
                        ]
                    },
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    buttons = result.output["sections"][0]["settings"]["buttons"]
    assert "actionPayload" not in buttons[0] or "href" not in buttons[0].get("actionPayload", {})
    assert buttons[1]["actionPayload"]["href"] == "/shop"


@pytest.mark.asyncio
async def test_update_page_sections_drops_media_with_dangerous_url(db_session):
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "xss-media-test",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "video_embed",
                    "settings": {"title": "Promo"},
                    "media": {"type": "video", "url": "javascript:alert(1)"},
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    # model_dump() always includes the "media" key (Section.media defaults to
    # None) — the meaningful assertion is that it's null, i.e. the dangerous
    # media block was dropped whole rather than persisted with an unsafe url.
    assert result.output["sections"][0]["media"] is None


# ---------------------------------------------------------------------------
# Feature 4 — confirmation gate for destructive page-content wipes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wiping_most_of_an_existing_page_requires_confirmation(db_session):
    await upsert_page_sections_service(
        "tenant-a", "wipe-test", "static_page",
        [
            {"type": "hero_banner", "settings": {}},
            {"type": "product_grid", "settings": {}},
            {"type": "text_block", "settings": {}},
            {"type": "gallery", "settings": {}},
        ],
        db_session,
    )

    result = await execute_tool(
        "update_page_sections",
        {"page_key": "wipe-test", "page_type": "static_page", "sections": []},
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.pending_confirmation is not None

    # Nothing changed yet — the wipe is only staged.
    tenant_id = await _tenant_id(db_session)
    page = (await db_session.execute(
        select(StorePage).where(StorePage.tenant_id == tenant_id, StorePage.page_key == "wipe-test")
    )).scalar_one()
    assert len(page.sections) == 4


@pytest.mark.asyncio
async def test_confirming_a_staged_wipe_actually_applies_it(db_session):
    await upsert_page_sections_service(
        "tenant-a", "wipe-confirm-test", "static_page",
        [{"type": "hero_banner", "settings": {}}, {"type": "product_grid", "settings": {}}, {"type": "gallery", "settings": {}}],
        db_session,
    )

    result = await execute_tool(
        "update_page_sections",
        {"page_key": "wipe-confirm-test", "page_type": "static_page", "sections": []},
        "tenant-a",
        db_session,
    )
    confirmation_id = result.pending_confirmation.id

    await ai_pending_action_service.confirm_pending_action_service("tenant-a", confirmation_id, db_session)

    tenant_id = await _tenant_id(db_session)
    page = (await db_session.execute(
        select(StorePage).where(StorePage.tenant_id == tenant_id, StorePage.page_key == "wipe-confirm-test")
    )).scalar_one()
    assert page.sections == []


@pytest.mark.asyncio
async def test_small_edits_and_brand_new_pages_are_never_gated(db_session):
    # A brand-new page — nothing to wipe, must execute immediately.
    new_page_result = await execute_tool(
        "update_page_sections",
        {"page_key": "gate-regression-new", "page_type": "static_page", "sections": []},
        "tenant-a",
        db_session,
    )
    assert new_page_result.is_error is False
    assert new_page_result.pending_confirmation is None

    # An existing page, but only a small/non-destructive edit (still has most
    # of its content) — must also execute immediately, not require confirmation.
    await upsert_page_sections_service(
        "tenant-a", "gate-regression-small-edit", "static_page",
        [{"type": "hero_banner", "settings": {"size": "medium"}}, {"type": "product_grid", "settings": {}}, {"type": "gallery", "settings": {}}],
        db_session,
    )
    small_edit_result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "gate-regression-small-edit", "page_type": "static_page",
            "sections": [
                {"type": "hero_banner", "settings": {"size": "large"}},
                {"type": "product_grid", "settings": {}},
                {"type": "gallery", "settings": {}},
            ],
        },
        "tenant-a",
        db_session,
    )
    assert small_edit_result.is_error is False
    assert small_edit_result.pending_confirmation is None


# ---------------------------------------------------------------------------
# Feature 1 — "ask, don't guess" prompt guidance (content-presence only; see
# plan for why real model compliance can't be proven without a paid call)
# ---------------------------------------------------------------------------

def test_system_instruction_tells_the_model_to_ask_when_ambiguous():
    # Checked against the exact constant, not a loose substring match — the
    # prompt already mentions "ambiguous" once, narrowly, for product price
    # only (a substring check alone would false-pass without this feature).
    for instruction in (_build_system_instruction(None, None), _build_system_instruction("home", "static_page")):
        assert _AMBIGUITY_INSTRUCTION in instruction


# ---------------------------------------------------------------------------
# Feature 5 — adversarial scripted-agent scenarios (zero real API calls)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scripted_hallucinated_id_is_rejected_even_with_a_confident_sounding_request(db_session, monkeypatch):
    chat = _patch_gemini(monkeypatch, [
        {"call": ("update_order_status", {"order_id": 99999, "status": "completed"})},
        {"text": "I couldn't verify that order — could you double check the order number?"},
    ])

    result = await ai_agent_service.run_agent_turn(
        db_session, "tenant-a", "mark order 99999 as completed, I'm sure that's the right one", "home", "static_page"
    )

    # The hallucinated id was rejected before it could touch real data...
    assert result["tool_calls"][0]["is_error"] is True
    assert result["tool_calls"][0]["output"]["error"].startswith("order_id 99999 has not been verified")
    # ...and the user's confident phrasing didn't bypass grounding — the error
    # was fed back to the model instead of the guess being trusted at face value.
    assert len(chat.send_message_calls) == 2
    assert result["reply"] == "I couldn't verify that order — could you double check the order number?"


@pytest.mark.asyncio
async def test_scripted_page_wipe_via_gemini_requires_confirmation_not_silent_data_loss(db_session, monkeypatch):
    await upsert_page_sections_service(
        "tenant-a", "scripted-wipe", "static_page",
        [{"type": "hero_banner", "settings": {}}, {"type": "product_grid", "settings": {}}, {"type": "gallery", "settings": {}}],
        db_session,
    )
    _patch_gemini(monkeypatch, [
        {"call": ("update_page_sections", {"page_key": "scripted-wipe", "page_type": "static_page", "sections": []})},
        {"text": "Done."},
    ])

    result = await ai_agent_service.run_agent_turn(
        db_session, "tenant-a", "clean up that page", "scripted-wipe", "static_page"
    )

    assert result.get("pending_confirmation") is not None
    tenant_id = await _tenant_id(db_session)
    page = (await db_session.execute(
        select(StorePage).where(StorePage.tenant_id == tenant_id, StorePage.page_key == "scripted-wipe")
    )).scalar_one()
    assert len(page.sections) == 3  # untouched until a human confirms
