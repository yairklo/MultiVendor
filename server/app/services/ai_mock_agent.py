"""
A tiny rule-based stand-in for the real Gemini agent, used automatically when
GEMINI_API_KEY is not set so the feature is usable (and testable, with zero
network access) with no key required. It understands a handful of layout
commands (resize / move / add / remove a section) plus a simple "create a
product" pattern, and drives the exact same tool executor the real agent uses,
so the rest of the pipeline (sanitization, persistence, subscription limits) is
exercised identically either way.
"""
import re
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_tool_executor import execute_tool

SECTION_ALIASES: Dict[str, str] = {
    "hero banner": "hero_banner", "hero": "hero_banner", "banner": "hero_banner",
    "product grid": "product_grid", "products": "product_grid", "grid": "product_grid",
    "video": "video_embed", "video embed": "video_embed",
    "text block": "text_block", "text": "text_block",
    "gallery": "gallery",
    "button group": "button_group", "buttons": "button_group", "button": "button_group", "cta": "button_group",
    "table": "table",
}

SIZE_ORDER = ["small", "medium", "large"]


def _find_section_type(phrase: str) -> str | None:
    normalized = phrase.strip().lower()
    if normalized in SECTION_ALIASES:
        return SECTION_ALIASES[normalized]
    for alias, section_type in SECTION_ALIASES.items():
        if alias in normalized:
            return section_type
    return None


def _default_section_for(section_type: str) -> Dict[str, Any]:
    if section_type == "hero_banner":
        return {"id": "", "type": section_type, "settings": {"headline": "New Banner", "size": "medium", "alignment": "center"}}
    if section_type == "product_grid":
        return {"id": "", "type": section_type, "settings": {"title": "Products", "columns": 4, "collection": "all"}}
    if section_type == "video_embed":
        return {"id": "", "type": section_type, "settings": {"title": "New Video", "autoplay": False}}
    if section_type == "text_block":
        return {"id": "", "type": section_type, "settings": {"heading": "New Section", "body": ""}}
    if section_type == "gallery":
        return {"id": "", "type": section_type, "settings": {"layout": "grid", "thumbnails": True}}
    if section_type == "button_group":
        return {
            "id": "", "type": section_type,
            "settings": {"buttons": [
                {"label": "Shop Now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"href": "/shop"}},
                {"label": "Add to Cart", "variant": "secondary", "actionType": "ADD_TO_CART"},
            ]},
        }
    return {
        "id": "", "type": "table",
        "settings": {"headers": ["Plan", "Price", "Storage"], "rows": [["Basic", "$9/mo", "10GB"], ["Pro", "$29/mo", "100GB"]]},
    }


_PAGE_BACKGROUND_RE = re.compile(
    r"(?:the\s+)?(?:whole\s+|entire\s+)?page(?:'s)?\s+background(?:\s+color)?\s+(?:to\s+)?([a-z#][a-z0-9#]*)",
    re.IGNORECASE,
)

_CREATE_PRODUCT_RE = re.compile(
    r"(?:add|create)\s+a?\s*product\s+(?:called|named)\s+\"?([^\"$]+?)\"?\s+(?:for|at|priced at)\s+\$?(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "new-product"


async def run_mock_agent(
    user_message: str, tenant_slug: str, page_key: str, page_type: str, db: AsyncSession
) -> Dict[str, Any]:
    tool_calls: List[Dict[str, Any]] = []

    create_match = _CREATE_PRODUCT_RE.search(user_message)
    if create_match:
        name, price = create_match.group(1).strip(), float(create_match.group(2))
        slug = _slugify(name)
        args = {
            "name": {"en": name},
            "slug": slug,
            "base_price": price,
            "variants": [{"sku": slug.upper(), "stock_quantity": 10}],
            "images": [],
        }
        result = await execute_tool("create_product", args, tenant_slug, db)
        tool_calls.append({"name": "create_product", "input": args, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I tried to create that product but it failed (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        return {"reply": f"Done (mock mode) — created product '{name}' at ${price:.2f}.", "tool_calls": tool_calls}

    get_result = await execute_tool("get_page_schema", {"page_key": page_key, "page_type": page_type}, tenant_slug, db)
    tool_calls.append({"name": "get_page_schema", "input": {"page_key": page_key, "page_type": page_type}, "output": get_result.output, "is_error": get_result.is_error})

    is_new_page = False
    if get_result.is_error:
        # update_page_sections creates the page if it doesn't exist yet, so a
        # "not found" here just means we're starting from an empty page rather
        # than a real failure — anything else (e.g. tenant not found) still bails.
        error_message = str(get_result.output.get("error", ""))
        if "No page found" not in error_message:
            return {"reply": f"I couldn't load that page (mock mode): {error_message or 'unknown error'}", "tool_calls": tool_calls}
        is_new_page = True

    sections: List[Dict[str, Any]] = [] if is_new_page else list(get_result.output["sections"])
    actions: List[str] = []
    msg = user_message.lower()

    # Page-level background is checked separately from the per-section clauses
    # below — it's a request about the page as a whole, not any one section.
    page_bg_match = _PAGE_BACKGROUND_RE.search(msg)
    page_background_color = page_bg_match.group(1) if page_bg_match else None
    if page_background_color:
        actions.append(f"set the page background to {page_background_color}")
        msg = msg[: page_bg_match.start()] + msg[page_bg_match.end() :]

    clauses = [c.strip() for c in re.split(r"\band\b", msg) if c.strip()]

    for clause in clauses:
        resize_match = re.search(r"(larger|bigger|smaller)", clause)
        move_match = re.search(r"move\s+(?:the\s+)?([a-z_ ]+?)\s+(above|below)\s+(?:the\s+)?([a-z_ ]+)", clause)
        remove_match = re.search(r"(?:remove|delete)\s+(?:the\s+)?([a-z_ ]+)", clause)
        add_match = re.search(r"add\s+(?:a\s+|an\s+)?([a-z_ ]+)", clause)

        if move_match:
            subj_phrase, direction, target_phrase = move_match.groups()
            subj_type = _find_section_type(subj_phrase)
            target_type = _find_section_type(target_phrase)
            if subj_type and target_type:
                subj_idx = next((i for i, s in enumerate(sections) if s["type"] == subj_type), -1)
                if subj_idx != -1:
                    subj = sections.pop(subj_idx)
                    target_idx = next((i for i, s in enumerate(sections) if s["type"] == target_type), -1)
                    insert_at = len(sections) if target_idx == -1 else (target_idx if direction == "above" else target_idx + 1)
                    sections.insert(insert_at, subj)
                    actions.append(f"moved {subj_type} {direction} {target_type}")
        elif resize_match and not remove_match and not add_match:
            direction = -1 if resize_match.group(1) == "smaller" else 1
            subj_type = _find_section_type(clause) or "hero_banner"
            idx = next((i for i, s in enumerate(sections) if s["type"] == subj_type), -1)
            if idx != -1:
                current = sections[idx]["settings"].get("size", "medium")
                current_idx = SIZE_ORDER.index(current) if current in SIZE_ORDER else 1
                next_idx = min(len(SIZE_ORDER) - 1, max(0, current_idx + direction))
                sections[idx] = {**sections[idx], "settings": {**sections[idx]["settings"], "size": SIZE_ORDER[next_idx]}}
                actions.append(f"resized {subj_type} to {SIZE_ORDER[next_idx]}")
        elif remove_match:
            subj_type = _find_section_type(remove_match.group(1))
            if subj_type:
                before = len(sections)
                sections = [s for s in sections if s["type"] != subj_type]
                if len(sections) < before:
                    actions.append(f"removed {subj_type}")
        elif add_match:
            subj_type = _find_section_type(add_match.group(1))
            if subj_type:
                sections.append(_default_section_for(subj_type))
                actions.append(f"added a new {subj_type}")

    if not actions:
        return {
            "reply": (
                "I'm running in offline mock mode (no GEMINI_API_KEY set), so I only understand simple commands "
                "like \"make the hero banner larger\", \"move the video above the products\", \"add a gallery\", "
                "\"remove the text block\", or \"add a product called X for $Y\". Try one of those, or set "
                "GEMINI_API_KEY to use the real Gemini agent."
            ),
            "tool_calls": tool_calls,
        }

    update_args: Dict[str, Any] = {"page_key": page_key, "page_type": page_type, "sections": sections}
    if page_background_color:
        update_args["background_color"] = page_background_color
    update_result = await execute_tool("update_page_sections", update_args, tenant_slug, db)
    tool_calls.append({"name": "update_page_sections", "input": update_args, "output": update_result.output, "is_error": update_result.is_error})

    if update_result.is_error:
        return {"reply": f"I tried to update the page but it failed: {update_result.output.get('error')}", "tool_calls": tool_calls}

    return {"reply": f"Done (mock mode) — {', '.join(actions)}.", "tool_calls": tool_calls}
