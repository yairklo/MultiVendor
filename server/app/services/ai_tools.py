"""
Provider-agnostic tool declarations for the AI layout & product assistant.
`parameters` is a plain JSON Schema object (lowercase "type" values) so it can be
adapted to whichever function-calling convention a given LLM API expects — see
`ai_agent_service.to_gemini_schema` for the Gemini-specific conversion.
"""
from typing import Any, Dict, List, TypedDict


class ToolDefinition(TypedDict):
    name: str
    description: str
    parameters: Dict[str, Any]


_SECTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Stable unique identifier for this section. Reuse the existing id when editing a "
            "section in place; omit it when adding a brand new section (the server will generate one).",
        },
        "type": {
            "type": "string",
            "enum": ["hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table"],
            "description": "The section component type to render.",
        },
        "settings": {
            "type": "object",
            "description": (
                "Arbitrary type-specific settings — use exactly these key names, the frontend components only "
                "read these: hero_banner: {headline, size: 'small'|'medium'|'large', alignment: 'left'|'center'|"
                "'right'}. product_grid: {title, columns (number), category_id?: number} renders REAL live "
                "products from this store, filtered to that category if category_id is given (look it up via the "
                "store's categories if the user names one) or the newest products otherwise — never invent "
                "product data yourself, this section always pulls the real catalog. video_embed: {title, autoplay "
                "(bool)}. text_block: {heading, body}. gallery: {layout: 'grid'|'carousel', thumbnails (bool)}. "
                "table: {title?, headers: string[], rows: string[][] (each row same length as headers)}. "
                "button_group: {buttons: [{label, variant?: 'primary'|'secondary'|'outline', actionType: "
                "'NAVIGATE'|'OPEN_MODAL'|'ADD_TO_CART'|'APPLY_COUPON', actionPayload?}]} — note actionType/"
                "actionPayload are camelCase, unlike every other snake_case field in this API; they are "
                "dispatched to the frontend as structured data, never executed as code, and any button with an "
                "unrecognized actionType (or the wrong casing) is silently dropped. For actionType=NAVIGATE, "
                "actionPayload MUST always be an object — a raw string is dropped and the button ends up dead: "
                "use {page_key: '<key>'} (always page_type='static_page') to link to another page on THIS store, "
                "including a brand new one you are creating in the same or a follow-up update_page_sections call "
                "— you do not know and must never guess this store's URL, the frontend resolves page_key to the "
                "correct link automatically. Only use {href: '/some/path'} for a fixed, non-page destination "
                "(e.g. '/shop'). On any section type, background_color/background/theme_color/theme and "
                "text_color/color are honored as CSS colors."
            ),
        },
        "media": {
            "type": "object",
            "description": "Optional media attached to the section (image or video).",
            "properties": {
                "type": {"type": "string", "enum": ["image", "video"]},
                "url": {"type": "string"},
                "aspect_ratio": {"type": "string"},
            },
            "required": ["type", "url"],
        },
    },
    "required": ["type", "settings"],
}

_VARIANT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "sku": {"type": "string"},
        "attributes_json": {"type": "object", "description": "e.g. {color: 'red', size: 'M'}"},
        "price_override": {"type": "number"},
        "stock_quantity": {"type": "number"},
    },
    "required": ["sku", "stock_quantity"],
}

ai_tools: List[ToolDefinition] = [
    {
        "name": "list_page_targets",
        "description": (
            "List all available pages and templates that can be edited for the current vendor's store, along "
            "with their page_key, page_type, title, and current section count. Call this when you need to "
            "discover what pages exist or the user hasn't specified one."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_categories",
        "description": (
            "List this vendor's real product categories (id, name, slug). Call this before setting "
            "product_grid.category_id on a section, or before creating a product with a category, so you use a "
            "real category id instead of guessing one."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_page_schema",
        "description": (
            "Fetch the current JSON section tree for a specific page or template, identified by page_key and "
            "page_type. Always call this before proposing an edit so you know the current section order, ids, "
            "and settings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_key": {"type": "string", "description": "The unique key of the page or template, e.g. 'home'."},
                "page_type": {
                    "type": "string",
                    "enum": ["static_page", "template"],
                    "description": "Whether the target is a static page or a reusable template.",
                },
            },
            "required": ["page_key", "page_type"],
        },
    },
    {
        "name": "update_page_sections",
        "description": (
            "Replace the full sections array for a page/template with an updated one, to reorder, resize, add, "
            "remove, or otherwise modify sections and their media/settings. You must pass the COMPLETE desired "
            "sections array (not a diff) — include unchanged sections as-is, keeping their existing id. If the "
            "page/template doesn't exist yet, it is created. IMPORTANT: when the user asks to change 'the page "
            "background' / 'the whole page' / the page's overall color (as opposed to one specific section like "
            "'the hero banner'), set the top-level background_color/text_color params below — NOT "
            "settings.background_color inside an individual section, which only colors that one section's card "
            "and leaves the rest of the page unchanged."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_key": {"type": "string", "description": "The unique key of the page or template being updated."},
                "page_type": {
                    "type": "string",
                    "enum": ["static_page", "template"],
                    "description": "Whether the target is a static page or a reusable template.",
                },
                "sections": {
                    "type": "array",
                    "description": "The full, ordered list of sections that should exist on the page after this update.",
                    "items": _SECTION_SCHEMA,
                },
                "background_color": {
                    "type": "string",
                    "description": (
                        "The PAGE's own background color (any CSS color) — shows in the margins and the gaps "
                        "between sections, not just inside one section. Omit to leave it unchanged from its "
                        "current value; pass an empty string to clear it back to the default."
                    ),
                },
                "text_color": {
                    "type": "string",
                    "description": "The PAGE's own default text color, same omit/empty-string rules as background_color.",
                },
            },
            "required": ["page_key", "page_type", "sections"],
        },
    },
    {
        "name": "create_product",
        "description": (
            "Create a new product in the current vendor's catalog. Always ask the user for (or sensibly infer) "
            "a name, price, and at least one SKU/variant before calling this — it creates a real, live product."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "object",
                    "description": "Localized product name, e.g. {en: 'Classic T-Shirt', he: '...'}. At least 'en' is required.",
                },
                "slug": {"type": "string", "description": "URL slug, lowercase letters/numbers/hyphens only, e.g. 'classic-tshirt'."},
                "description": {"type": "object", "description": "Localized product description, same shape as name."},
                "base_price": {"type": "number", "description": "Price as a positive number."},
                "category_id": {"type": "number", "description": "Optional existing category id."},
                "variants": {
                    "type": "array",
                    "description": "At least one variant/SKU with a stock quantity.",
                    "items": _VARIANT_SCHEMA,
                },
                "images": {
                    "type": "array",
                    "description": "Optional list of image URLs.",
                    "items": {"type": "string"},
                },
            },
            "required": ["name", "slug", "base_price", "variants"],
        },
    },
    # --- Catalog & inventory management ---------------------------------
    {
        "name": "get_product",
        "description": "Fetch a single product's current full details (name, price, description, category, active status, variants). Call before update_product/archive_product/update_inventory so you know current values.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "number"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "update_product",
        "description": "Partially update a product — only the fields you pass are changed, everything else stays as-is. Use for name/price/description/category/product_type changes, or is_active for a manual publish/unpublish. To fully remove a product from sale, prefer archive_product (clearer intent).",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "number"},
                "name": {"type": "object", "description": "Localized name, e.g. {en: '...', he: '...'}."},
                "description": {"type": "object", "description": "Localized description, same shape as name."},
                "base_price": {"type": "number"},
                "category_id": {"type": "number"},
                "product_type": {"type": "string", "enum": ["physical", "digital", "service"]},
                "is_active": {"type": "boolean"},
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "archive_product",
        "description": "Take a product off sale without deleting it (sets it inactive — it disappears from the storefront but all its data, images, and reviews are kept, and it can be reactivated later via update_product). This is the normal, safe way to 'remove' a product — prefer it over delete_product whenever the user just wants it gone from the store.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "number"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "delete_product",
        "description": (
            "PERMANENTLY delete a product and all its images/reviews/variants — this cannot be undone. "
            "This tool NEVER deletes anything itself: calling it only stages the deletion and returns a "
            "confirmation id: the user must click a real Confirm button in the UI before anything is actually "
            "deleted. Tell the user clearly what you're staging and that you're waiting on their confirmation — "
            "never say it's done until they've actually confirmed. If the user just wants the product to stop "
            "being sold, use archive_product instead — it's reversible and doesn't need confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "number"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "update_inventory",
        "description": "Adjust a specific variant's stock quantity (set it to a new absolute number, e.g. 0 to mark out of stock). Only stock_quantity changes — sku/price on that variant are left exactly as they are. Call get_product first if you don't already know the variant_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "variant_id": {"type": "number"},
                "stock_quantity": {"type": "number", "description": "The new absolute stock count (not a delta)."},
            },
            "required": ["variant_id", "stock_quantity"],
        },
    },
    {
        "name": "add_product_variant",
        "description": "Add a brand new SKU/variant to an existing product (e.g. a new size or color).",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "number"},
                "sku": {"type": "string"},
                "attributes_json": {"type": "object", "description": "e.g. {color: 'red', size: 'M'}"},
                "price_override": {"type": "number", "description": "Optional — overrides the product's base_price for this variant only."},
                "stock_quantity": {"type": "number"},
            },
            "required": ["product_id", "sku", "stock_quantity"],
        },
    },
    # --- Coupons & promotions ---------------------------------------------
    {
        "name": "create_coupon",
        "description": "Create a new discount coupon code.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "3-20 chars, e.g. 'SUMMER10'."},
                "discount_type": {"type": "string", "enum": ["percentage", "fixed"]},
                "discount_val": {"type": "number", "description": "10 for 10% if percentage, or a currency amount if fixed."},
                "min_order_amt": {"type": "number", "description": "Optional minimum order subtotal to use this coupon."},
                "usage_limit": {"type": "number", "description": "Optional max total redemptions."},
                "valid_until": {"type": "string", "description": "ISO8601 expiration datetime."},
            },
            "required": ["code", "discount_type", "discount_val", "valid_until"],
        },
    },
    {
        "name": "list_coupons",
        "description": "List this store's coupons with their code, discount, usage, expiry, and active status.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "toggle_coupon_status",
        "description": "Enable or disable an existing coupon. A disabled coupon is immediately rejected at checkout, even if it hasn't expired or hit its usage limit yet.",
        "parameters": {
            "type": "object",
            "properties": {
                "coupon_id": {"type": "number"},
                "is_active": {"type": "boolean"},
            },
            "required": ["coupon_id", "is_active"],
        },
    },
    # --- Orders & fulfillment ----------------------------------------------
    {
        "name": "list_orders",
        "description": "List this store's orders, most recent first, with optional filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending_payment", "processing", "completed", "cancelled", "expired"]},
                "start_date": {"type": "string", "description": "ISO8601 — only orders created on/after this."},
                "end_date": {"type": "string", "description": "ISO8601 — only orders created on/before this."},
                "customer_email": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "get_order_details",
        "description": "Fetch one order's full item breakdown, totals, shipping info, and status.",
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "number"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "update_order_status",
        "description": (
            "Change an order's status. Moving to 'processing' or 'completed' happens immediately. Moving to "
            "'cancelled' NEVER happens immediately — like delete_product, this only stages the cancellation and "
            "returns a confirmation id; a human must click Confirm in the UI before the order actually cancels "
            "and its stock is restored. Tell the user you're waiting on confirmation, don't claim it's cancelled yet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "number"},
                "status": {"type": "string", "enum": ["processing", "completed", "cancelled"]},
            },
            "required": ["order_id", "status"],
        },
    },
    # --- Analytics (read-only) ----------------------------------------------
    {
        "name": "get_sales_analytics",
        "description": "Revenue/AOV/order-count totals plus a daily breakdown and top-selling products for a date range. Only counts orders that were actually paid (processing/completed). Present this as a Markdown table in your reply, don't just restate the raw numbers in prose.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO8601, e.g. '2026-01-01'."},
                "end_date": {"type": "string", "description": "ISO8601, e.g. '2026-12-31'."},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_customer_insights",
        "description": "Customer-base metrics: total customers, repeat-purchase rate, top spenders, and most recent signups.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_inventory_health",
        "description": "Lists every active product's variants that are out of stock or running low, so you can flag restocking needs. Present as a Markdown table when there are several.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]


def to_gemini_function_declarations() -> List[Dict[str, Any]]:
    return [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in ai_tools]
