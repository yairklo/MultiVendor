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


# Recursive JSON Schema via $defs/$ref — a section can itself be a container ("grid_container",
# "two_column_layout") holding other sections. $defs is hoisted onto the tool's top-level
# `parameters` object (see update_page_sections below) since a "#/$defs/..." $ref resolves
# against the schema document root, not the immediate parent object. Confirmed by reading
# ai_agent_service.py: decl["parameters"] is passed straight through to
# types.FunctionDeclaration(parameters_json_schema=...) with zero transformation, so $defs/$ref
# reach the Gemini SDK call untouched. children/zones are deliberately kept as non-required
# Section properties (true by omission below) — the google-genai SDK's docs note recursive refs
# are only supported within non-required properties.
_SECTION_SCHEMA_DEFS: Dict[str, Any] = {
    "Section": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "Stable unique identifier for this section. Reuse the existing id when editing a "
                "section in place; omit it when adding a brand new section (the server will generate one).",
            },
            "type": {
                "type": "string",
                "enum": [
                    "hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table",
                    "grid_container", "two_column_layout", "feature_highlights", "testimonials",
                ],
                "description": "The section component type to render.",
            },
            "settings": {
                "type": "object",
                "description": (
                    "Arbitrary type-specific settings — use exactly these key names, the frontend components only "
                    "read these. IMPORTANT — every field marked (localized) below is an object with one key per "
                    "this store's supported_languages (look them up via get_page_schema's tenant context or ask if "
                    "unsure — e.g. {\"en\": \"Summer Sale\", \"he\": \"מבצע קיץ\"}), NEVER a plain string; the save "
                    "is rejected if any supported language is missing. hero_banner: {headline (localized), size: "
                    "'small'|'medium'|'large', alignment: 'left'|'center'|'right'}. product_grid: {title (localized), "
                    "columns (number), category_id?: number, card_style?: 'default'|'framed'|'minimal'} renders "
                    "REAL live products from this store, filtered to that category if category_id is given (look it "
                    "up via the store's categories if the user names one) or the newest products otherwise — never "
                    "invent product data yourself, this section always pulls the real catalog and every card "
                    "already has a working Add to Cart button; card_style only changes how the card looks, never "
                    "what it does. video_embed: {title (localized), autoplay (bool)}. "
                    "text_block: {heading (localized), body (localized)}. gallery: {title? (localized), layout: "
                    "'grid'|'carousel', images?: string[] (real image URLs — shows placeholder boxes if omitted)}. "
                    "table: {title? (localized), headers: [localized, ...] (one per column), rows: [[localized, ...], "
                    "...] (each row same length as headers, every cell localized)}. "
                    "button_group: {buttons: [{label (localized), variant?: 'primary'|'secondary'|'outline', "
                    "actionType: 'NAVIGATE'|'OPEN_MODAL'|'ADD_TO_CART'|'APPLY_COUPON', actionPayload?}]} — note "
                    "actionType/actionPayload are camelCase, unlike every other snake_case field in this API; they "
                    "are dispatched to the frontend as structured data, never executed as code, and any button with "
                    "an unrecognized actionType (or the wrong casing) is silently dropped. For actionType=NAVIGATE, "
                    "actionPayload MUST always be an object — a raw string is dropped and the button ends up dead: "
                    "use {page_key: '<key>'} (always page_type='static_page') to link to another page on THIS store, "
                    "including a brand new one you are creating in the same or a follow-up update_page_sections call "
                    "— you do not know and must never guess this store's URL, the frontend resolves page_key to the "
                    "correct link automatically. Only use {href: '/some/path'} for a fixed, non-page destination "
                    "(e.g. '/shop'). feature_highlights: {title? (localized), items: [{icon?: string (a lucide-react "
                    "icon name like 'Truck'|'ShieldCheck'|'RotateCcw'|'Sparkles'), title (localized), text "
                    "(localized)}]} — a row of short value-prop cards (e.g. free shipping / secure payment / easy "
                    "returns). testimonials: {title? (localized), items: [{quote (localized), author (localized), "
                    "role? (localized)}]} — customer quote cards. On any leaf section type, background_color/"
                    "background/theme_color/theme and text_color/color are honored as CSS colors (these are NOT "
                    "localized — plain color strings). grid_container: {columns (number, e.g. 3), design_variant?: "
                    "'primary'|'accent'|'secondary'|'muted'|'neutral'}. two_column_layout: {design_variant?: same 5 "
                    "values}. Containers do NOT read background_color — design_variant is the only way to theme a "
                    "grid_container/two_column_layout."
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
            "children": {
                "type": "array",
                "description": "Only for type='grid_container' — the child sections rendered inside the grid.",
                "items": {"$ref": "#/$defs/Section"},
            },
            "zones": {
                "type": "object",
                "description": "Only for type='two_column_layout'. Keys 'left'/'right', each an array of child sections.",
                "properties": {
                    "left": {"type": "array", "items": {"$ref": "#/$defs/Section"}},
                    "right": {"type": "array", "items": {"$ref": "#/$defs/Section"}},
                },
            },
        },
        "required": ["type", "settings"],
    }
}
_SECTION_SCHEMA: Dict[str, Any] = {"$ref": "#/$defs/Section"}

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
        "name": "create_category",
        "description": "Create a product category in this store. name is localized {lang: str} for every supported language.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "object", "description": "Localized category name, e.g. {en: 'Mugs', he: 'ספלים'}."},
                "slug": {"type": "string", "description": "URL slug, lowercase letters/numbers/hyphens."},
                "parent_id": {"type": "number", "description": "Optional parent category id."},
            },
            "required": ["name", "slug"],
        },
    },
    {
        "name": "update_category",
        "description": "Partially update a category's name, slug, or parent. Only fields you pass are changed.",
        "parameters": {
            "type": "object",
            "properties": {
                "category_id": {"type": "number"},
                "name": {"type": "object", "description": "Localized category name."},
                "slug": {"type": "string"},
                "parent_id": {"type": "number"},
            },
            "required": ["category_id"],
        },
    },
    {
        "name": "delete_category",
        "description": (
            "PERMANENTLY delete a category. This tool NEVER deletes anything itself: calling it only stages "
            "the deletion and returns a confirmation id. A human must click Confirm in the UI."
        ),
        "parameters": {
            "type": "object",
            "properties": {"category_id": {"type": "number"}},
            "required": ["category_id"],
        },
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
            "and leaves the rest of the page unchanged. If this call would remove most/all of an existing page's "
            "current sections, it doesn't apply immediately — it stages the change and returns a pending "
            "confirmation the user must click, same as delete_product; tell them plainly what you've staged."
        ),
        "parameters": {
            "type": "object",
            "$defs": _SECTION_SCHEMA_DEFS,
            "properties": {
                "page_key": {"type": "string", "description": "The unique key of the page or template being updated."},
                "page_type": {
                    "type": "string",
                    "enum": ["static_page", "template"],
                    "description": "Whether the target is a static page or a reusable template.",
                },
                "sections": {
                    "type": "array",
                    "description": (
                        "The full, ordered list of sections that should exist on the page after this update. Use a "
                        "grid_container for 3+ related items that should sit side by side (put a product_grid, "
                        "button_group, or text_block as each child in 'children') and a two_column_layout for "
                        "exactly two side-by-side blocks (children go in zones.left/zones.right). Nesting is capped "
                        "at 3 levels server-side — don't nest a container inside a container more than 2 levels deep."
                    ),
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
                "product_type": {
                    "type": "string",
                    "enum": ["physical", "digital", "service"],
                    "description": "Defaults to physical. Digital products do not use stock/shipping.",
                },
                "show_in_marketplace": {"type": "boolean", "description": "Whether this product appears on the marketplace."},
                "digital_file_url": {
                    "type": "string",
                    "description": "Required for digital products. Real http(s) or /uploads/... URL. Never invent a URL.",
                },
                "download_limit": {"type": "number", "description": "Optional max downloads for a digital product."},
                "variants": {
                    "type": "array",
                    "description": "At least one variant/SKU with a stock quantity.",
                    "items": _VARIANT_SCHEMA,
                },
                "images": {
                    "type": "array",
                    "description": "Optional list of real http(s) or /uploads/... image URLs. First is primary. Never invent a URL.",
                    "items": {"type": "string"},
                },
            },
            "required": ["name", "slug", "base_price", "variants"],
        },
    },
    {
        "name": "bulk_import_products",
        "description": (
            "Create or update many products/inventory levels in one call from spreadsheet-style rows -- the "
            "standard way to act on an attached .xlsx. Upserts by sku: a sku that already exists in this "
            "store gets its stock_quantity/base_price updated, and image_url replaced when provided; a new sku "
            "creates a new product with one variant. Use this instead of calling create_product repeatedly "
            "when the user attached a spreadsheet or otherwise gave you more than a couple of products at once. "
            "image_url must be a real http(s) or /uploads/... URL — never invent one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "description": "One entry per product/SKU.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name_en": {"type": "string", "description": "Required for a new sku; applied on an existing sku when provided."},
                            "name_he": {"type": "string", "description": "Applied on create and when updating an existing sku."},
                            "slug": {"type": "string", "description": "Required for a new sku; lowercase letters/numbers/hyphens."},
                            "description_en": {"type": "string", "description": "Applied on create and when updating an existing sku."},
                            "base_price": {"type": "number"},
                            "sku": {"type": "string", "description": "Required -- the upsert key."},
                            "stock_quantity": {"type": "integer"},
                            "category_id": {"type": "number"},
                            "image_url": {
                                "type": "string",
                                "description": "Real http(s) or /uploads/... image URL. Applied on create and when updating an existing sku. Never invent a URL.",
                            },
                        },
                        "required": ["sku", "base_price", "stock_quantity"],
                    },
                },
            },
            "required": ["rows"],
        },
    },
    # --- Storefront templates ---------------------------------------------
    {
        "name": "list_storefront_templates",
        "description": (
            "List the 3 premium storefront templates a seller can pick from (key, name, tagline, color swatch). "
            "Call this when the user wants to change their store's overall look, asks what templates are "
            "available, or hasn't picked one yet."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "apply_storefront_template",
        "description": (
            "Switch this store to one of the 3 premium templates — seeds fresh, on-brand home/about/contact "
            "pages and publishes them immediately, so the change is live right away. This OVERWRITES whatever "
            "is currently on the home/about/contact pages, including anything the seller has customized, so it "
            "always requires the user's explicit confirmation first: this tool never applies anything itself, "
            "it only stages the change and returns a confirmation id — a human must click Confirm in the UI. "
            "Never say the template has been applied until they've actually confirmed. After it's confirmed, "
            "sections on the new pages can be further customized the same way as any other page, with "
            "get_page_schema/update_page_sections."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "template_key": {
                    "type": "string",
                    "description": "One of the keys returned by list_storefront_templates, e.g. 'aurora'.",
                },
            },
            "required": ["template_key"],
        },
    },
    # --- Catalog & inventory management ---------------------------------
    {
        "name": "list_products",
        "description": (
            "Search this store's catalog by name, description, or SKU — including inactive products when "
            "include_inactive is true. ALWAYS use this (never get_inventory_health) when looking up a product "
            "by name or SKU so you can get the real product_id before get_product/update_product."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Optional name/SKU/description search, any supported language."},
                "include_inactive": {"type": "boolean", "description": "If true, include archived/inactive products. Default false."},
                "category_id": {"type": "number"},
                "limit": {"type": "number", "description": "Max rows to return, default 20, hard-capped at 50."},
            },
            "required": [],
        },
    },
    {
        "name": "get_product",
        "description": "Fetch a single product's current full details (name, price, description, category, active status, variants, images). Call before update_product/archive_product/update_inventory so you know current values.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "number"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "update_product",
        "description": (
            "Partially update a product — only the fields you pass are changed, everything else stays as-is. "
            "Use for name/price/description/category/product_type/is_active, or to set photos via images. "
            "images is a full replace of the gallery (first URL becomes the primary). Only pass real http(s) "
            "or /uploads/... URLs — never invent a link. To fully remove a product from sale, prefer archive_product."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "number"},
                "name": {"type": "object", "description": "Localized name, e.g. {en: '...', he: '...'}."},
                "description": {"type": "object", "description": "Localized description, same shape as name."},
                "base_price": {"type": "number"},
                "category_id": {"type": "number"},
                "product_type": {"type": "string", "enum": ["physical", "digital", "service"]},
                "show_in_marketplace": {"type": "boolean"},
                "digital_file_url": {
                    "type": "string",
                    "description": "http(s) or /uploads/... URL for a digital product. Never invent a URL.",
                },
                "download_limit": {"type": "number"},
                "is_active": {"type": "boolean"},
                "images": {
                    "type": "array",
                    "description": "Full replace of product image URLs. First item is primary. Omit to leave images unchanged; pass [] to clear them.",
                    "items": {"type": "string"},
                },
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
    {
        "name": "update_variant",
        "description": (
            "Update an existing variant's price override, SKU, attribute options, and/or inventory. "
            "Only fields you pass are changed. Call get_product first so the variant_id is grounded."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "variant_id": {"type": "number"},
                "sku": {"type": "string"},
                "attributes_json": {"type": "object", "description": "e.g. {color: 'red', size: 'M'}"},
                "price_override": {"type": "number"},
                "stock_quantity": {"type": "number"},
            },
            "required": ["variant_id"],
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
    {
        "name": "update_coupon",
        "description": "Partially update a coupon (code, discount, min order, usage limit, expiry, active flag). Only fields you pass are changed.",
        "parameters": {
            "type": "object",
            "properties": {
                "coupon_id": {"type": "number"},
                "code": {"type": "string", "description": "3-20 chars."},
                "discount_type": {"type": "string", "enum": ["percentage", "fixed"]},
                "discount_val": {"type": "number"},
                "min_order_amt": {"type": "number"},
                "usage_limit": {"type": "number"},
                "valid_until": {"type": "string", "description": "ISO8601 expiration datetime."},
                "is_active": {"type": "boolean"},
            },
            "required": ["coupon_id"],
        },
    },
    {
        "name": "delete_coupon",
        "description": (
            "PERMANENTLY delete a coupon. This tool NEVER deletes anything itself: calling it only stages "
            "the deletion and returns a confirmation id. A human must click Confirm in the UI."
        ),
        "parameters": {
            "type": "object",
            "properties": {"coupon_id": {"type": "number"}},
            "required": ["coupon_id"],
        },
    },
    # --- Orders & fulfillment ----------------------------------------------
    {
        "name": "list_orders",
        "description": (
            "List this store's orders, most recent first, with optional filters. Always capped server-side "
            "(defaults to 20, max 50) regardless of how many orders the store actually has — narrow with "
            "status/date/customer filters rather than expecting every order back at once."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending_payment", "processing", "completed", "cancelled", "expired"]},
                "start_date": {"type": "string", "description": "ISO8601 — only orders created on/after this."},
                "end_date": {"type": "string", "description": "ISO8601 — only orders created on/before this."},
                "customer_email": {"type": "string"},
                "limit": {"type": "number", "description": "Max rows to return, default 20, hard-capped at 50."},
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
    {
        "name": "fulfill_order",
        "description": (
            "Stage a real courier shipment (HFD or Lionwheel) for a processing physical order. This NEVER "
            "creates the shipment itself — like delete_product, it only stages a confirmation the human must "
            "click. Optional provider_override must be 'hfd' or 'lionwheel'. Tracking comes from the courier "
            "after confirm — do not invent a tracking number, and never tell the user it shipped until they "
            "confirm."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "number"},
                "provider_override": {
                    "type": "string",
                    "enum": ["hfd", "lionwheel"],
                    "description": "Optional courier. Omit to use the store's default.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "export_orders_csv",
        "description": (
            "Summarize this store's orders for export. The assistant cannot attach a CSV file — tell the "
            "user to download it from Admin → Reports. Returns row_count only; never claim a file was generated."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
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
    {
        "name": "list_reviews",
        "description": "List this store's product reviews (pending and approved) for moderation.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "number", "description": "Max rows to return, default 20, hard-capped at 50."},
            },
            "required": [],
        },
    },
    {
        "name": "set_review_status",
        "description": "Set a review's moderation status to approved, rejected, or pending.",
        "parameters": {
            "type": "object",
            "properties": {
                "review_id": {"type": "number"},
                "status": {"type": "string", "enum": ["approved", "rejected", "pending"]},
            },
            "required": ["review_id", "status"],
        },
    },
    {
        "name": "list_customers",
        "description": "Read-only search of this store's customers (email, name, order count, spend) matching the admin customers panel.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Optional email or name filter."},
                "limit": {"type": "number", "description": "Max rows to return, default 20, hard-capped at 50."},
            },
            "required": [],
        },
    },
    {
        "name": "get_store_settings",
        "description": (
            "Fetch this store's branding and settings (logo, currency, languages, nav, theme color) plus "
            "Stripe Connect connection status. Stripe onboarding is a browser OAuth flow — report status "
            "and direct the user to Store Settings; do not attempt to connect Stripe yourself."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_store_settings",
        "description": (
            "Partially update store settings: logo_url, banner_url, primary_color, currency, "
            "supported_languages, default_language, nav_items, support_email, custom_css, review flags. "
            "There is no favicon field. Image URLs must be real http(s) or /uploads/... paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "logo_url": {"type": "string"},
                "banner_url": {"type": "string"},
                "primary_color": {"type": "string", "description": "CSS color / branding theme token."},
                "currency": {"type": "string"},
                "custom_css": {"type": "string"},
                "support_email": {"type": "string"},
                "supported_languages": {"type": "array", "items": {"type": "string"}},
                "default_language": {"type": "string"},
                "review_moderation_enabled": {"type": "boolean"},
                "allow_unverified_reviews": {"type": "boolean"},
                "nav_items": {
                    "type": "array",
                    "description": "Primary navigation menu items matching the admin settings schema.",
                    "items": {"type": "object"},
                },
            },
            "required": [],
        },
    },
    {
        "name": "list_page_versions",
        "description": "List saved versions of a page so you can revert to a real version_id instead of guessing one.",
        "parameters": {
            "type": "object",
            "properties": {
                "page_key": {"type": "string"},
                "page_type": {"type": "string", "enum": ["static_page", "template"]},
            },
            "required": ["page_key", "page_type"],
        },
    },
    {
        "name": "publish_page",
        "description": (
            "Publish the current draft of a page to the live storefront. This NEVER publishes immediately — "
            "it stages an AIPendingAction; a human must click Confirm. Never auto-publish drafts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_key": {"type": "string"},
                "page_type": {"type": "string", "enum": ["static_page", "template"]},
            },
            "required": ["page_key", "page_type"],
        },
    },
    {
        "name": "revert_page_version",
        "description": (
            "Roll a page's draft back to a previous version. This NEVER reverts immediately — it stages an "
            "AIPendingAction; a human must click Confirm. Look up version_id via list_page_versions first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_key": {"type": "string"},
                "page_type": {"type": "string", "enum": ["static_page", "template"]},
                "version_id": {"type": "number"},
            },
            "required": ["page_key", "page_type", "version_id"],
        },
    },
    {
        "name": "list_shipping_configs",
        "description": "List this store's configured shipping providers (hfd/lionwheel) and which is default.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "delete_shipping_config",
        "description": (
            "Remove a shipping provider config. This NEVER deletes immediately — it stages an AIPendingAction; "
            "a human must click Confirm. Look up the provider via list_shipping_configs first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "enum": ["hfd", "lionwheel"]},
            },
            "required": ["provider"],
        },
    },
    {
        "name": "upgrade_subscription",
        "description": (
            "Upgrade this store's subscription plan. This NEVER upgrades immediately — it stages an "
            "AIPendingAction; a human must click Confirm."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_plan_code": {"type": "string", "enum": ["free", "pro", "enterprise"]},
            },
            "required": ["target_plan_code"],
        },
    },
]


def to_gemini_function_declarations() -> List[Dict[str, Any]]:
    return [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in ai_tools]
