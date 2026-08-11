"""
Guardrail tests for the AI co-pilot: the validation self-correction retry loop,
ID-grounding enforcement (no guessing entity ids), and the trimming of failed
retry rounds out of the persisted Gemini history.

The retry-loop tests drive app.services.ai_agent_service.run_agent_turn end to
end against a tiny scripted fake of the google.genai chat API (never a real
network call) so the actual loop/branching logic in run_agent_turn is what's
under test, not a re-implementation of it. The grounding tests call
execute_tool directly, same style as tests/test_ai_admin_copilot.py.
"""
import google.genai as genai
import pytest
from google.genai import types

from app.services import ai_agent_service
from app.services.ai_tool_executor import ToolGroundingContext, execute_tool


# ---------------------------------------------------------------------------
# Fake Gemini chat — records every send_message call and replays a scripted
# sequence of responses (each either a single tool call or a final text reply),
# building real google.genai Content objects so the history-trimming code under
# test operates on the same shapes it would in production.
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


# ---------------------------------------------------------------------------
# Validation retry loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_loop_lets_model_self_correct_a_malformed_tool_call(db_session, monkeypatch):
    chat = _patch_gemini(monkeypatch, [
        {"call": ("get_product", {"product_id": 1})},
        {"call": ("update_product", {"product_id": 1, "base_price": -20})},  # invalid: base_price must be > 0
        {"call": ("update_product", {"product_id": 1, "base_price": 25})},   # corrected
        {"text": "Updated the price to 25."},
    ])

    result = await ai_agent_service.run_agent_turn(db_session, "tenant-a", "set the price to -20", "home", "static_page")

    assert result["used_provider"] == "gemini"
    assert result["reply"] == "Updated the price to 25."
    assert [c["name"] for c in result["tool_calls"]] == ["get_product", "update_product", "update_product"]
    assert result["tool_calls"][1]["is_error"] is True
    assert result["tool_calls"][2]["is_error"] is False

    # The error sent back to the model must be the structured shape the guardrail
    # promises — a labeled error type plus the correctable detail, not a raw 500.
    error_round_parts = chat.send_message_calls[2]
    error_response = error_round_parts[0].function_response.response
    assert error_response["error"] == "ValidationFailed"
    assert "base_price" in str(error_response["details"]).lower() or "0" in str(error_response["details"])

    # It really did land: re-reading the product shows the corrected price.
    check = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert float(check.output["base_price"]) == 25


@pytest.mark.asyncio
async def test_retry_loop_gives_up_after_max_retries_without_looping_forever(db_session, monkeypatch):
    chat = _patch_gemini(monkeypatch, [
        {"call": ("get_product", {"product_id": 1})},
        {"call": ("update_product", {"product_id": 1, "base_price": -1})},
        {"call": ("update_product", {"product_id": 1, "base_price": -2})},
        {"call": ("update_product", {"product_id": 1, "base_price": -3})},
        {"call": ("update_product", {"product_id": 1, "base_price": -4})},
        {"text": "this should never be reached"},
    ])

    result = await ai_agent_service.run_agent_turn(db_session, "tenant-a", "set a bad price", "home", "static_page")

    # 4 consecutive failures (1 initial + 3 retries) trip MAX_VALIDATION_RETRIES — the
    # loop must stop itself rather than exhausting MAX_TOOL_TURNS (6) or looping forever.
    assert len(chat.send_message_calls) == 5
    assert result["reply"] != "this should never be reached"
    assert "tried" in result["reply"].lower() or "error" in result["reply"].lower()
    failed = [c for c in result["tool_calls"] if c["name"] == "update_product"]
    assert len(failed) == 4
    assert all(c["is_error"] for c in failed)

    # Price was never actually written.
    check = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert float(check.output["base_price"]) == 10.0


@pytest.mark.asyncio
async def test_persisted_history_drops_the_failed_retry_round_after_success(db_session, monkeypatch):
    from app.services import ai_conversation_service

    _patch_gemini(monkeypatch, [
        {"call": ("get_product", {"product_id": 1})},
        {"call": ("update_product", {"product_id": 1, "base_price": -20})},
        {"call": ("update_product", {"product_id": 1, "base_price": 25})},
        {"text": "Updated the price to 25."},
    ])

    await ai_agent_service.run_agent_turn(db_session, "tenant-a", "set the price to -20", "home", "static_page")

    stored = await ai_conversation_service.load_gemini_history_json("tenant-a", "home", "static_page", db_session)

    def _update_product_calls(history):
        calls = []
        for content in history:
            for part in content.get("parts", []):
                fc = part.get("function_call")
                if fc and fc.get("name") == "update_product":
                    calls.append(fc["args"])
        return calls

    update_calls = _update_product_calls(stored)
    # The abandoned -20 attempt must not survive into what gets replayed as context on
    # the next turn — only the grounding read and the corrected write remain.
    assert update_calls == [{"product_id": 1, "base_price": 25}]


# ---------------------------------------------------------------------------
# ID grounding (no guessing entity ids)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_product_is_rejected_without_a_prior_lookup(db_session):
    context = ToolGroundingContext()
    result = await execute_tool(
        "update_product", {"product_id": 1, "base_price": 999}, "tenant-a", db_session, context
    )
    assert result.is_error is True
    assert result.error_type == "UngroundedReference"

    unchanged = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert float(unchanged.output["base_price"]) == 10.0


@pytest.mark.asyncio
async def test_update_product_succeeds_once_get_product_has_grounded_the_id(db_session):
    context = ToolGroundingContext()
    grounding_read = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session, context)
    assert grounding_read.is_error is False

    result = await execute_tool(
        "update_product", {"product_id": 1, "base_price": 42}, "tenant-a", db_session, context
    )
    assert result.is_error is False
    assert float(result.output["base_price"]) == 42


@pytest.mark.asyncio
async def test_update_inventory_requires_a_grounded_variant_id(db_session):
    context = ToolGroundingContext()
    ungrounded = await execute_tool(
        "update_inventory", {"variant_id": 1, "stock_quantity": 5}, "tenant-a", db_session, context
    )
    assert ungrounded.is_error is True
    assert ungrounded.error_type == "UngroundedReference"

    # get_product surfaces its variants' ids, which is enough to ground them.
    await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session, context)
    grounded = await execute_tool(
        "update_inventory", {"variant_id": 1, "stock_quantity": 5}, "tenant-a", db_session, context
    )
    assert grounded.is_error is False
    assert grounded.output["stock_quantity"] == 5


@pytest.mark.asyncio
async def test_update_order_status_requires_a_grounded_order_id(db_session):
    context = ToolGroundingContext()
    ungrounded = await execute_tool(
        "update_order_status", {"order_id": 1, "status": "processing"}, "tenant-a", db_session, context
    )
    assert ungrounded.is_error is True
    assert ungrounded.error_type == "UngroundedReference"

    await execute_tool("list_orders", {}, "tenant-a", db_session, context)
    grounded = await execute_tool(
        "update_order_status", {"order_id": 1, "status": "processing"}, "tenant-a", db_session, context
    )
    assert grounded.is_error is False


@pytest.mark.asyncio
async def test_grounding_is_not_enforced_when_no_context_is_supplied(db_session):
    # Every other existing caller of execute_tool (mock agent, unit tests) doesn't
    # pass a context — grounding must stay opt-in so it doesn't break them.
    result = await execute_tool("update_product", {"product_id": 1, "base_price": 55}, "tenant-a", db_session)
    assert result.is_error is False
