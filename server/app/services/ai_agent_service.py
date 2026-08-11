from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import ai_conversation_service
from app.services.ai_mock_agent import run_mock_agent
from app.services.ai_tool_executor import execute_tool
from app.services.ai_tools import to_gemini_function_declarations

MAX_TOOL_TURNS = 6

_SYSTEM_INSTRUCTION_TEMPLATE = (
    "You are an AI layout and product assistant for a multi-vendor e-commerce admin panel. "
    "You edit a page's JSON section tree, and can create new products, on behalf of a single vendor using the "
    "provided tools — every tool call you make is automatically scoped to that vendor's own store, you never "
    "need to (and cannot) specify which vendor. "
    "The user is currently editing page_key=\"{page_key}\" page_type=\"{page_type}\". "
    "Always call get_page_schema first to see the current sections and their ids before editing a page. "
    "Call exactly ONE tool per turn and wait for its result before calling another — never call multiple tools "
    "in parallel in the same turn. "
    "When calling update_page_sections you MUST pass the full desired sections array (not a diff), preserving "
    "the ids of unchanged sections and omitting id only for brand new sections. "
    "Use a button_group section for calls-to-action or clickable actions, and a table section for structured "
    "comparisons or specs. "
    "'Change the page background' (or 'the whole page') means the top-level background_color param of "
    "update_page_sections, not a section's own settings.background_color — the latter only recolors that one "
    "section's card and would leave the rest of the page looking unchanged, which is not what the user asked "
    "for. Only set a section's settings.background_color when the user names that specific section. "
    "You can create additional static pages beyond the one currently open — call update_page_sections with a "
    "new, descriptive page_key (page_type='static_page') and it is created automatically. If the user asks for "
    "a button that leads to a page that doesn't exist yet, create that page first (or in the same reply), then "
    "add the button with actionType=NAVIGATE and actionPayload={{page_key: '<the new page's page_key>'}} — never "
    "put a guessed URL in actionPayload.href for an internal page, you don't know this store's URL structure. "
    "When the user asks you to add or create a product, call create_product with a sensible name, slug, price, "
    "and at least one variant/SKU — ask a brief clarifying question first only if the price is genuinely "
    "ambiguous or missing. "
    "After the tools report success, reply to the user in one or two short sentences describing what changed."
)


def is_gemini_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _build_gemini_tools():
    from google.genai import types

    declarations = []
    for decl in to_gemini_function_declarations():
        has_properties = bool(decl["parameters"].get("properties"))
        declarations.append(
            types.FunctionDeclaration(
                name=decl["name"],
                description=decl["description"],
                **({"parameters_json_schema": decl["parameters"]} if has_properties else {}),
            )
        )
    return [types.Tool(function_declarations=declarations)]


async def _persist_turn(
    tenant_slug: str, page_key: str, page_type: str, user_message: str, result: Dict[str, Any], db: AsyncSession,
    gemini_history_json: List[Dict[str, Any]] | None = None,
) -> None:
    new_messages = [
        {"role": "user", "text": user_message},
        {"role": "assistant", "text": result["reply"], "tool_calls": result["tool_calls"]},
    ]
    await ai_conversation_service.save_conversation_turn(
        tenant_slug, page_key, page_type, new_messages, db, gemini_history_json=gemini_history_json
    )


async def run_agent_turn(
    db: AsyncSession, tenant_slug: str, user_message: str, page_key: str, page_type: str
) -> Dict[str, Any]:
    if not is_gemini_configured():
        result = await run_mock_agent(user_message, tenant_slug, page_key, page_type, db)
        result = {**result, "used_provider": "mock"}
        # Mock mode has no real multi-turn reasoning to preserve, but the visible
        # transcript is still persisted so reopening this page shows it.
        await _persist_turn(tenant_slug, page_key, page_type, user_message, result, db)
        return result

    from google.genai import Client, types

    client = Client(api_key=settings.GEMINI_API_KEY)
    tools = _build_gemini_tools()
    system_instruction = _SYSTEM_INSTRUCTION_TEMPLATE.format(page_key=page_key, page_type=page_type)

    stored_history_json = await ai_conversation_service.load_gemini_history_json(
        tenant_slug, page_key, page_type, db
    )
    restored_history = (
        [types.Content.model_validate(c) for c in stored_history_json] if stored_history_json else None
    )

    chat = client.aio.chats.create(
        model=settings.GEMINI_MODEL,
        config=types.GenerateContentConfig(tools=tools, system_instruction=system_instruction),
        history=restored_history,
    )

    tool_calls: List[Dict[str, Any]] = []
    response = await chat.send_message(user_message)

    for _ in range(MAX_TOOL_TURNS):
        function_calls = response.function_calls or []
        if not function_calls:
            result = {"reply": (response.text or "").strip() or "Done.", "tool_calls": tool_calls, "used_provider": "gemini"}
            break

        response_parts = []
        for call in function_calls:
            tool_result = await execute_tool(call.name, dict(call.args or {}), tenant_slug, db)
            tool_calls.append({"name": call.name, "input": call.args, "output": tool_result.output, "is_error": tool_result.is_error})
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name,
                    response={"error": tool_result.output} if tool_result.is_error else {"result": tool_result.output},
                )
            )

        response = await chat.send_message(response_parts)
    else:
        result = {
            "reply": "I made several changes but hit the tool-call limit for this turn — check the preview and ask me to continue if needed.",
            "tool_calls": tool_calls,
            "used_provider": "gemini",
        }

    history_json = [c.model_dump(mode="json", exclude_none=True) for c in chat.get_history()]
    await _persist_turn(tenant_slug, page_key, page_type, user_message, result, db, gemini_history_json=history_json)
    return result
