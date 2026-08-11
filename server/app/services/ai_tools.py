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
]


def to_gemini_function_declarations() -> List[Dict[str, Any]]:
    return [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in ai_tools]
