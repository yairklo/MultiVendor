import asyncio
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import ai_conversation_service
from app.services.ai_mock_agent import run_mock_agent
from app.services.ai_tool_executor import READ_TOOLS, WRITE_TOOLS, ToolGroundingContext, execute_tool
from app.services.ai_tools import to_gemini_function_declarations

MAX_TOOL_TURNS = 14

# A tool call that fails validation/grounding isn't fatal — its error is fed back to
# the model as the next turn's input so it can self-correct. But an unbounded retry
# budget risks looping forever on a request it fundamentally can't satisfy, so
# consecutive failures (reset by any success) are capped here: after this many in a
# row, the turn ends with one clear user-facing error instead of continuing to
# bounce off the model.
MAX_VALIDATION_RETRIES = 3

_SYSTEM_INSTRUCTION_HEADER = (
    "You are a proactive store-management co-pilot for a multi-vendor e-commerce admin panel — a full "
    "assistant to the store owner, not just a layout editor. You can edit a page's JSON section tree; create, "
    "update, archive, or (with confirmation) delete products and categories; manage variants, inventory, "
    "coupons, reviews, store settings, and shipping; look up customers and orders; fulfill orders; and pull "
    "sales/customer/inventory analytics — all via the provided tools, every one of which is automatically "
    "scoped to this vendor's own store. You never need to (and cannot) specify which vendor. "
)

# Used when this chat IS scoped to a real page (the per-page layout editor).
_PAGE_CONTEXT_INSTRUCTION = (
    "The user is currently editing page_key=\"{page_key}\" page_type=\"{page_type}\" (only relevant to the page-"
    "layout tools — most of your tools aren't about any particular page at all). "
)

# Used when this chat is the tenant-wide global copilot — there is no current page at all.
_NO_PAGE_CONTEXT_INSTRUCTION = (
    "This conversation is NOT scoped to any specific page — you're the general store copilot, with no page "
    "currently open. If the user wants to view or edit a page's layout, call list_page_targets first to see "
    "what pages/templates exist, or ask them which page (or what new page_key) they mean, before calling "
    "get_page_schema or update_page_sections. Never invent, reuse, or guess a placeholder page_key such as "
    "'global' — every page-layout tool call must use a real page_key the user named or list_page_targets "
    "returned. "
)

_AMBIGUITY_INSTRUCTION = (
    "If a request doesn't clearly identify which page, product, order, or other entity it's about — or is "
    "otherwise too vague or confusing to act on with confidence — reply asking a short clarifying question "
    "instead of guessing which one was meant. This is about WHICH target, not whether to act: once the target "
    "is clear, the 'just do it' rule below for reversible changes still applies unchanged. "
)

_SYSTEM_INSTRUCTION_TEMPLATE = (
    "{context_instruction}"
    "{ambiguity_instruction}"
    "You may call multiple READ tools in the same turn (list_products, get_product, list_categories, "
    "list_orders, …) so you can gather context in parallel. Mutation/write tools must run one at a time — "
    "never mix a write with other tools in the same turn, and never fire two writes together. Prefer a read "
    "tool before an update when you don't already know the current state. "
    "Never fabricate or guess entity ids (product_id, variant_id, coupon_id, order_id, category_id, "
    "review_id, version_id). If the user names an item by title, code, or number instead of giving you its "
    "id directly, you MUST first call the matching lookup tool — list_products (never get_inventory_health) "
    "for products by name/SKU, list_categories, list_coupons, list_orders, get_order_details, list_reviews, "
    "list_page_versions — to retrieve the real id from the database before calling any update/archive/delete/"
    "toggle tool with it. The server enforces this and will reject an id it hasn't seen you look up this "
    "conversation with an UngroundedReference error — if you see that error, call the suggested lookup tool "
    "and then retry with the id it returns, don't retry with the same guessed id. "
    "For sales reports, low-stock lists, or any other multi-row result, reply with a Markdown table — don't just "
    "restate numbers in prose. "
    "delete_product, delete_category, delete_coupon, delete_shipping_config, update_order_status(status="
    "'cancelled'), apply_storefront_template, publish_page, revert_page_version, and upgrade_subscription "
    "NEVER complete immediately, no matter how clearly the user asks — calling them only stages the action "
    "and returns a pending confirmation that renders as a real button in the UI; only the user clicking it "
    "actually runs it. Never auto-confirm, never auto-publish drafts, never invent image URLs. Tell the user "
    "plainly what you've staged and that you're waiting on their confirmation — never say it's done until it "
    "actually is. For anything reversible (archiving, editing, inventory/coupon changes, marking an order "
    "processing/completed), just do it — don't ask permission first. "
    "To add or change product photos, pass images on update_product (after list_products/get_product) or "
    "image_url on bulk_import_products. Both the create path and an existing-SKU update persist the URL. Only "
    "use real http(s) or /uploads/... links (user-supplied, an attachment URL, or a known public image host) "
    "— never invent a URL. Never tell the user an image was added unless the tool result's images or "
    "primary_image_url actually contains that URL. "
    "Stripe Connect is a browser OAuth flow: report connection status via get_store_settings and direct the "
    "user to Store Settings. You cannot connect Stripe yourself. "
    "\n\nPage-layout specifics: always call get_page_schema first to see the current sections and their ids "
    "before editing a page. When calling update_page_sections you MUST pass the full desired sections array "
    "(not a diff), preserving the ids of unchanged sections and omitting id only for brand new sections. Use a "
    "button_group section for calls-to-action or clickable actions, and a table section for structured "
    "comparisons or specs. "
    "'Change the page background' (or 'the whole page') means the top-level background_color param of "
    "update_page_sections, not a section's own settings.background_color — the latter only recolors that one "
    "section's card and would leave the rest of the page looking unchanged, which is not what the user asked "
    "for. Only set a section's settings.background_color when the user names that specific section. "
    "Use a grid_container section (settings.columns, children: [...]) when the user wants 3 or more related "
    "items side by side — e.g. 'a 3-column grid with a button in each column' means one grid_container with "
    "columns=3 and three button_group children in its children array, NOT three separate top-level sections. "
    "Use a two_column_layout section (zones.left/zones.right) for exactly two side-by-side blocks, e.g. an "
    "image/text split. Every item inside a grid_container's children array or a two_column_layout's "
    "zones.left/zones.right MUST be a complete, self-contained section object with its own type and settings, "
    "inlined directly at that position — NEVER a bare id string or a pointer to a section defined elsewhere. A "
    "section belongs in exactly one place in the tree: if it lives inside a zone/children array, do not also "
    "list it again as a separate top-level (or sibling) entry. "
    "Nesting is capped at 3 levels server-side — don't nest containers inside containers more "
    "than 2 levels deep. A container's own free-text background_color is ignored; the only way to theme a "
    "grid_container/two_column_layout is settings.design_variant ('primary'|'accent'|'secondary'|'muted'|"
    "'neutral'), unlike the 7 original section types which use background_color/text_color. "
    "You can create additional static pages at any time — call update_page_sections with a "
    "new, descriptive page_key (page_type='static_page') and it is created automatically. If the user asks for "
    "a button that leads to a page that doesn't exist yet, create that page first (or in the same reply), then "
    "add the button with actionType=NAVIGATE and actionPayload={{page_key: '<the new page's page_key>'}} — never "
    "put a guessed URL in actionPayload.href for an internal page, you don't know this store's URL structure. "
    "When the user asks you to add or create a product, call create_product with a sensible name, slug, price, "
    "and at least one variant/SKU — ask a brief clarifying question first only if the price is genuinely "
    "ambiguous or missing. "
    "After the tools report success, reply to the user in one or two short sentences describing what changed "
    "(more for a report/table, which should be the bulk of the reply)."
)


def is_gemini_configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


_DEGENERATE_INPUT_REPLY = (
    "I couldn't understand that message — could you rephrase what you'd like me to do?"
)


def _is_degenerate_input(message: str) -> bool:
    """
    True for input carrying no real signal: empty/whitespace-only, or
    character-level spam (a single character, or a short repeating pattern of
    2-5 characters) making up the overwhelming majority of the message.
    Deliberately language-agnostic — no word lists — so it never
    false-positives on short legitimate Hebrew/English text; it only trips on
    degenerate patterns like "aaaaaaaa..." or "asdasdasd...". Checked before
    any Gemini call so junk input never costs a real API call.
    """
    stripped = message.strip()
    if not stripped:
        return True
    if len(stripped) < 8:
        return False  # too short for a repetition signal to mean anything

    most_common_count = max(stripped.count(c) for c in set(stripped))
    if most_common_count / len(stripped) > 0.9:
        return True

    for period in range(2, 6):
        if len(stripped) < period * 3:
            continue
        pattern = stripped[:period]
        repeated = (pattern * (len(stripped) // period + 1))[: len(stripped)]
        matches = sum(1 for a, b in zip(stripped, repeated) if a == b)
        if matches / len(stripped) > 0.9:
            return True

    return False


def _build_system_instruction(page_key: Optional[str], page_type: Optional[str]) -> str:
    context_instruction = (
        _PAGE_CONTEXT_INSTRUCTION.format(page_key=page_key, page_type=page_type)
        if page_key is not None
        else _NO_PAGE_CONTEXT_INSTRUCTION
    )
    return _SYSTEM_INSTRUCTION_HEADER + _SYSTEM_INSTRUCTION_TEMPLATE.format(
        context_instruction=context_instruction, ambiguity_instruction=_AMBIGUITY_INSTRUCTION
    )


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
    tenant_slug: str, page_key: Optional[str], page_type: Optional[str], user_message: str,
    result: Dict[str, Any], db: AsyncSession,
    gemini_history_json: List[Dict[str, Any]] | None = None,
) -> None:
    new_messages = [
        {"role": "user", "text": user_message},
        {"role": "assistant", "text": result["reply"], "tool_calls": result["tool_calls"]},
    ]
    await ai_conversation_service.save_conversation_turn(
        tenant_slug, page_key, page_type, new_messages, db, gemini_history_json=gemini_history_json
    )


def _content_has_part(content: Any, part_attr: str) -> bool:
    return any(getattr(part, part_attr, None) is not None for part in (content.parts or []))


def _trim_history_for_persistence(history: List[Any], round_results: List[Dict[str, Any]]) -> List[Any]:
    """
    `history` is the raw google.genai Content[] for this turn (chat.get_history()).
    `round_results[i]` = {"calls": [{"tool_name", "is_error"}, ...]} for the i-th
    function-call round this turn, in order. Because chat.send_message(user_message)
    seeds history[0] (user) / history[1] (model) before the loop starts, round i's
    function_call Content lives at history[2*i + 1] and its function_response at
    history[2*i + 2] — a parallel-read round still occupies one pair, with multiple
    parts inside each Content.

    Drops two things before this gets persisted and replayed as context on every
    future turn:
      - a failed round's call/response pair, once a LATER round this same turn
        retried every failed tool from that round and those retries succeeded —
        the model already self-corrected, so the abandoned attempt is just noise.
      - a trailing function_call with no matching function_response, which happens
        when the loop stops (retry cap or MAX_TOOL_TURNS) without sending one more
        message to Gemini — left in place it would replay as an unresolved dangling
        tool call next turn.
    """
    drop_indices = set()
    for i, r in enumerate(round_results):
        failed_names = [c["tool_name"] for c in r["calls"] if c["is_error"]]
        if not failed_names:
            continue
        later_success = set()
        for later in round_results[i + 1:]:
            for c in later["calls"]:
                if not c["is_error"]:
                    later_success.add(c["tool_name"])
        if all(name in later_success for name in failed_names):
            drop_indices.add(2 * i + 1)
            drop_indices.add(2 * i + 2)

    trimmed = [c for idx, c in enumerate(history) if idx not in drop_indices]
    if trimmed and _content_has_part(trimmed[-1], "function_call") and not _content_has_part(trimmed[-1], "function_response"):
        trimmed = trimmed[:-1]
    return trimmed


async def run_agent_turn(
    db: AsyncSession, tenant_slug: str, user_message: str, page_key: Optional[str], page_type: Optional[str],
    attachment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    # A dropped file carries its own signal even with no/blank message text —
    # skip the degenerate-input short-circuit in that case, and give the
    # model something to act on instead of an empty string.
    if attachment and not (user_message or "").strip():
        user_message = "Please look at the attached file and take the appropriate action."

    # What gets persisted to the visible chat transcript -- short and
    # readable, regardless of how much attachment content gets appended to
    # what actually gets sent to the model below.
    display_message = user_message
    if attachment:
        display_message = f"{user_message}\n\n[Attached file: {attachment['filename']}]"

    if not attachment and _is_degenerate_input(user_message):
        # Checked before is_gemini_configured()/client construction on purpose —
        # junk input never reaches (and never costs) a real Gemini call, mock or not.
        result = {"reply": _DEGENERATE_INPUT_REPLY, "tool_calls": [], "used_provider": "mock"}
        await _persist_turn(tenant_slug, page_key, page_type, display_message, result, db)
        return result

    # Text sent to the model this turn -- augmented with parsed spreadsheet
    # rows (Gemini can't read .xlsx bytes) or, for an image, just the saved
    # URL (the raw bytes go in as a separate multimodal part below instead).
    augmented_message = user_message
    image_part_kwargs: Optional[Dict[str, Any]] = None
    if attachment and attachment["kind"] == "spreadsheet":
        augmented_message = (
            f"{user_message}\n\nThe user attached a spreadsheet (\"{attachment['filename']}\"), already parsed "
            f"into {attachment['parsed']['total_count']} row(s) ({attachment['parsed']['valid_count']} valid). "
            f"Use the bulk_import_products tool with this exact data if the user wants to import/update "
            f"products or inventory from it -- do not ask them to re-describe the rows. Parsed rows as JSON: "
            f"{attachment['parsed']['rows']}"
        )
    elif attachment and attachment["kind"] == "image":
        augmented_message = (
            f"{user_message}\n\nThe user attached an image, saved at URL \"{attachment['url']}\" -- it's also "
            f"included below so you can see it directly. If they want a product created from it, use that URL "
            f"in create_product's images argument."
        )
        image_part_kwargs = {"data": attachment["bytes"], "mime_type": attachment["mime_type"]}

    if not is_gemini_configured():
        result = await run_mock_agent(augmented_message, tenant_slug, page_key, page_type, db)
        result = {**result, "used_provider": "mock"}
        # Mock mode has no real multi-turn reasoning to preserve, but the visible
        # transcript is still persisted so reopening this page shows it.
        await _persist_turn(tenant_slug, page_key, page_type, display_message, result, db)
        return result

    from google.genai import Client, types

    client = Client(api_key=settings.GEMINI_API_KEY)
    tools = _build_gemini_tools()
    system_instruction = _build_system_instruction(page_key, page_type)

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
    # One entry per function-call round this turn, in order — used only to decide what
    # to drop from the persisted Gemini history afterwards (see _trim_history_for_persistence).
    round_results: List[Dict[str, Any]] = []
    pending_confirmation = None
    grounding_context = ToolGroundingContext()
    prior_messages = await ai_conversation_service.get_conversation_messages_service(
        tenant_slug, page_key, page_type, db
    )
    for msg in prior_messages:
        for prior_call in (msg.tool_calls or []):
            if not prior_call.is_error:
                grounding_context.seed_from_tool_output(prior_call.name, prior_call.output)
    consecutive_failures = 0
    last_error_detail: Any = None
    message_parts = (
        [types.Part.from_text(text=augmented_message), types.Part.from_bytes(**image_part_kwargs)]
        if image_part_kwargs else augmented_message
    )
    response = await chat.send_message(message_parts)

    for _ in range(MAX_TOOL_TURNS):
        function_calls = response.function_calls or []
        if not function_calls:
            result = {"reply": (response.text or "").strip() or "Done.", "tool_calls": tool_calls, "used_provider": "gemini"}
            break

        names = [c.name for c in function_calls]
        run_parallel = (
            len(function_calls) > 1
            and all(n in READ_TOOLS for n in names)
            and not any(n in WRITE_TOOLS for n in names)
        )
        if run_parallel:
            tool_results = list(await asyncio.gather(*[
                execute_tool(c.name, dict(c.args or {}), tenant_slug, db, grounding_context)
                for c in function_calls
            ]))
        else:
            tool_results = [
                await execute_tool(c.name, dict(c.args or {}), tenant_slug, db, grounding_context)
                for c in function_calls
            ]

        response_parts = []
        round_had_error = False
        round_calls: List[Dict[str, Any]] = []
        for call, tool_result in zip(function_calls, tool_results):
            tool_calls.append({"name": call.name, "input": call.args, "output": tool_result.output, "is_error": tool_result.is_error})
            round_calls.append({"tool_name": call.name, "is_error": tool_result.is_error})
            if tool_result.pending_confirmation:
                pending_confirmation = tool_result.pending_confirmation
            if tool_result.is_error:
                round_had_error = True
                last_error_detail = tool_result.output
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name,
                    response=(
                        {"error": tool_result.error_type, "details": tool_result.output}
                        if tool_result.is_error else {"result": tool_result.output}
                    ),
                )
            )
        round_results.append({"calls": round_calls})

        consecutive_failures = consecutive_failures + 1 if round_had_error else 0
        if consecutive_failures > MAX_VALIDATION_RETRIES:
            # Deliberately don't send this round's results back to Gemini — we're
            # done retrying, so no more API calls are needed for this turn.
            result = {
                "reply": (
                    f"I tried {MAX_VALIDATION_RETRIES + 1} times to complete that but kept hitting validation "
                    f"errors — the last one was: {last_error_detail}. Could you double-check the details (or "
                    f"rephrase what you'd like) and I'll try again?"
                ),
                "tool_calls": tool_calls,
                "used_provider": "gemini",
            }
            break

        response = await chat.send_message(response_parts)
    else:
        result = {
            "reply": "I made several changes but hit the tool-call limit for this turn — check the preview and ask me to continue if needed.",
            "tool_calls": tool_calls,
            "used_provider": "gemini",
        }

    if pending_confirmation:
        result["pending_confirmation"] = pending_confirmation.model_dump(mode="json")

    trimmed_history = _trim_history_for_persistence(chat.get_history(), round_results)
    history_json = [c.model_dump(mode="json", exclude_none=True) for c in trimmed_history]
    await _persist_turn(tenant_slug, page_key, page_type, display_message, result, db, gemini_history_json=history_json)
    return result
