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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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

_INVENTORY_HEALTH_RE = re.compile(r"low.?stock|out.?of.?stock|inventory\s+(?:health|status)", re.IGNORECASE)
_SALES_REPORT_RE = re.compile(r"sales\s+report|how\s+much\s+revenue|revenue\s+report|sales\s+(?:this|for|summary)", re.IGNORECASE)
_LIST_ORDERS_RE = re.compile(r"list\s+orders|show\s+(?:me\s+)?(?:the\s+)?orders|recent\s+orders", re.IGNORECASE)
_LIST_PRODUCTS_RE = re.compile(r"list\s+products|find\s+(?:the\s+)?product|look\s+up\s+(?:the\s+)?product|search\s+products|show\s+products", re.IGNORECASE)
_LIST_CUSTOMERS_RE = re.compile(r"list\s+customers|show\s+(?:me\s+)?(?:the\s+)?customers", re.IGNORECASE)
_LIST_REVIEWS_RE = re.compile(r"list\s+reviews|show\s+(?:me\s+)?(?:the\s+)?reviews|pending\s+reviews", re.IGNORECASE)
_STORE_SETTINGS_RE = re.compile(r"store\s+settings|branding|stripe\s+connect|is\s+stripe\s+connected", re.IGNORECASE)
_CREATE_COUPON_RE = re.compile(
    r"create\s+a?\s*coupon\s+([A-Za-z0-9_-]+)\s+for\s+(\d+(?:\.\d+)?)%\s*off",
    re.IGNORECASE,
)


def _resolve_name(name: Any) -> str:
    if isinstance(name, dict):
        return name.get("en") or name.get("he") or next(iter(name.values()), "")
    return str(name)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "new-product"


def _escape_table_cell(value: Any) -> str:
    # Product/customer names are free text (including AI-generated ones) and can
    # legitimately contain "|" — unescaped, that would split into extra columns
    # and break the rendered table.
    return str(value).replace("|", "\\|")


def _format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(_escape_table_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


_NO_PAGE_FALLBACK_REPLY = (
    "I'm running in offline mock mode (no GEMINI_API_KEY set). From the general store copilot I understand "
    "\"show low stock\", \"sales report\", \"list orders\", \"list products\", \"list customers\", \"list reviews\", "
    "\"store settings\", \"add a product called X for $Y\", or \"create a coupon CODE for X% off\" — page-layout "
    "edits (resize/move/add/remove a section) need a specific page open, so try that from the page editor instead. "
    "Or set GEMINI_API_KEY to use the real Gemini agent."
)


async def run_mock_agent(
    user_message: str, tenant_slug: str, page_key: Optional[str], page_type: Optional[str], db: AsyncSession
) -> Dict[str, Any]:
    tool_calls: List[Dict[str, Any]] = []

    if _LIST_PRODUCTS_RE.search(user_message):
        q_match = re.search(r"(?:named|called|for|matching)\s+[\"']?([^\"'\n]+)[\"']?", user_message, re.IGNORECASE)
        args = {"query": q_match.group(1).strip(), "include_inactive": True} if q_match else {"include_inactive": True}
        result = await execute_tool("list_products", args, tenant_slug, db)
        tool_calls.append({"name": "list_products", "input": args, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't list products (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        products = result.output[:10]
        if not products:
            return {"reply": "Done (mock mode) — no matching products.", "tool_calls": tool_calls}
        rows = [[p["id"], _escape_table_cell(_resolve_name(p.get("name"))), p.get("slug"), p.get("base_price")] for p in products]
        table = _format_markdown_table(["Id", "Name", "Slug", "Price"], rows)
        return {"reply": f"Done (mock mode) — products:\n\n{table}", "tool_calls": tool_calls}

    if _LIST_CUSTOMERS_RE.search(user_message):
        result = await execute_tool("list_customers", {}, tenant_slug, db)
        tool_calls.append({"name": "list_customers", "input": {}, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't list customers (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        customers = result.output[:10]
        if not customers:
            return {"reply": "Done (mock mode) — no customers yet.", "tool_calls": tool_calls}
        rows = [[c.get("full_name"), c.get("email"), c.get("orders_count")] for c in customers]
        table = _format_markdown_table(["Name", "Email", "Orders"], rows)
        return {"reply": f"Done (mock mode) — customers:\n\n{table}", "tool_calls": tool_calls}

    if _LIST_REVIEWS_RE.search(user_message):
        result = await execute_tool("list_reviews", {}, tenant_slug, db)
        tool_calls.append({"name": "list_reviews", "input": {}, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't list reviews (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        reviews = result.output[:10]
        if not reviews:
            return {"reply": "Done (mock mode) — no reviews yet.", "tool_calls": tool_calls}
        rows = [[r.get("id"), r.get("product_name"), r.get("rating"), "approved" if r.get("is_approved") else "pending"] for r in reviews]
        table = _format_markdown_table(["Id", "Product", "Rating", "Status"], rows)
        return {"reply": f"Done (mock mode) — reviews:\n\n{table}", "tool_calls": tool_calls}

    if _STORE_SETTINGS_RE.search(user_message):
        result = await execute_tool("get_store_settings", {}, tenant_slug, db)
        tool_calls.append({"name": "get_store_settings", "input": {}, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't load store settings (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        stripe = result.output.get("stripe_connect") or {}
        connected = "connected" if stripe.get("is_connected") else "not connected"
        return {
            "reply": (
                f"Done (mock mode) — currency {result.output.get('currency')}, "
                f"languages {result.output.get('supported_languages')}. Stripe is {connected}. "
                f"{stripe.get('note', '')}"
            ),
            "tool_calls": tool_calls,
        }

    if _INVENTORY_HEALTH_RE.search(user_message):
        result = await execute_tool("get_inventory_health", {}, tenant_slug, db)
        tool_calls.append({"name": "get_inventory_health", "input": {}, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't check inventory (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        out_of_stock = result.output["out_of_stock"]
        low_stock = result.output["low_stock"]
        if not out_of_stock and not low_stock:
            return {"reply": "Done (mock mode) — inventory looks healthy, nothing out of stock or low.", "tool_calls": tool_calls}
        rows = [
            [i["sku"], i["stock_quantity"], "OUT OF STOCK" if i["stock_quantity"] <= 0 else "Low"]
            for i in (out_of_stock + low_stock)
        ]
        table = _format_markdown_table(["SKU", "Stock", "Status"], rows)
        return {"reply": f"Done (mock mode) — inventory health:\n\n{table}", "tool_calls": tool_calls}

    if _LIST_ORDERS_RE.search(user_message):
        result = await execute_tool("list_orders", {}, tenant_slug, db)
        tool_calls.append({"name": "list_orders", "input": {}, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't list orders (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        orders = result.output[:10]
        if not orders:
            return {"reply": "Done (mock mode) — no orders yet.", "tool_calls": tool_calls}
        rows = [[o["order_number"], o["status"], f"${o['total_amount']}"] for o in orders]
        table = _format_markdown_table(["Order", "Status", "Total"], rows)
        return {"reply": f"Done (mock mode) — most recent orders:\n\n{table}", "tool_calls": tool_calls}

    if _SALES_REPORT_RE.search(user_message):
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=30)
        args = {"start_date": start.date().isoformat(), "end_date": end.date().isoformat()}
        result = await execute_tool("get_sales_analytics", args, tenant_slug, db)
        tool_calls.append({"name": "get_sales_analytics", "input": args, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I couldn't pull a sales report (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        o = result.output
        reply = (
            f"Done (mock mode) — sales for the last 30 days: **${o['total_revenue']}** revenue, "
            f"**{o['orders_count']}** orders, **${o['aov']}** AOV."
        )
        return {"reply": reply, "tool_calls": tool_calls}

    coupon_match = _CREATE_COUPON_RE.search(user_message)
    if coupon_match:
        code, pct = coupon_match.group(1).upper(), float(coupon_match.group(2))
        valid_until = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        args = {"code": code, "discount_type": "percentage", "discount_val": pct, "valid_until": valid_until}
        result = await execute_tool("create_coupon", args, tenant_slug, db)
        tool_calls.append({"name": "create_coupon", "input": args, "output": result.output, "is_error": result.is_error})
        if result.is_error:
            return {"reply": f"I tried to create that coupon but it failed (mock mode): {result.output.get('error')}", "tool_calls": tool_calls}
        return {"reply": f"Done (mock mode) — created coupon '{code}' for {pct:.0f}% off, valid 30 days.", "tool_calls": tool_calls}

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

    if page_key is None:
        # No page open (the global copilot) — none of the section-editing commands
        # below apply without a real page_key, and unlike the real Gemini agent
        # there's no list_page_targets reasoning step in mock mode to fall back on.
        return {"reply": _NO_PAGE_FALLBACK_REPLY, "tool_calls": tool_calls}

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
                "\"remove the text block\", \"add a product called X for $Y\", \"show low stock\", \"sales "
                "report\", \"list orders\", \"list products\", \"list customers\", \"list reviews\", "
                "\"store settings\", or \"create a coupon CODE for X% off\". Try one of those, or set "
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
