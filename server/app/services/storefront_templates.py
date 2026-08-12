"""
Seed data for the 3 selectable premium storefront templates. Deliberately just plain Python
data structured exactly like the `sections` array `update_page_sections`/upsert_page_sections_service
already accepts — applying a template is nothing more than calling the same upsert path 3 times
(once per page_key below) with one of these dicts, which is what makes the result immediately
editable by the AI agent through its existing tools: it's just another StorePage row to it.

Imagery is Lorem Picsum placeholder photography (deterministic by seed, always resolves) — sellers
are expected to swap it for real product photography via the AI chat or admin editor.

TODO: STOREFRONT_TEMPLATES is a static in-code list for this MVP/feature branch — fine while
there are only 3 curated templates ship with the app, but it means adding/editing a template
requires a code change + deploy. If templates need to be authored without a release (e.g. more
templates, marketplace-style third-party templates, or per-tenant custom templates), move this
to a DB table (or versioned JSON files loaded at startup) instead of hardcoding it here.
"""
from typing import Any, Dict, List, TypedDict


class StorefrontTemplateMeta(TypedDict):
    key: str
    name: str
    tagline: str
    swatch: Dict[str, str]


class StorefrontTemplate(StorefrontTemplateMeta):
    pages: Dict[str, Dict[str, Any]]


def _picsum(seed: str, w: int = 1600, h: int = 900) -> str:
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"


AURORA: StorefrontTemplate = {
    "key": "aurora",
    "name": "Aurora",
    "tagline": "Soft, minimal, boutique-ready.",
    "swatch": {"bg": "#faf8f5", "text": "#1f2937", "accent": "#6366f1"},
    "pages": {
        "home": {
            "title": "Home",
            "background_color": "#faf8f5",
            "text_color": "#1f2937",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {
                        "headline": "Timeless pieces, thoughtfully made",
                        "size": "large",
                        "alignment": "center",
                        "background_color": "#f1ede7",
                        "text_color": "#1f2937",
                    },
                    "media": {"type": "image", "url": _picsum("aurora-hero"), "aspect_ratio": "16/9"},
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "Why shop with us",
                        "items": [
                            {"icon": "Truck", "title": "Free shipping", "text": "On every order, no minimum spend."},
                            {"icon": "ShieldCheck", "title": "Secure checkout", "text": "Your payment details always stay protected."},
                            {"icon": "RotateCcw", "title": "30-day returns", "text": "Not quite right? Send it back, no questions asked."},
                        ],
                    },
                },
                {
                    "type": "product_grid",
                    "settings": {"title": "New Arrivals", "columns": 4, "card_style": "minimal"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "muted"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "Our story",
                                    "body": (
                                        "We started with a simple idea: fewer, better things. Every piece in "
                                        "our collection is chosen for how it's made, not just how it looks — "
                                        "small runs, honest materials, and a supply chain we can actually stand behind."
                                    ),
                                },
                            },
                        ],
                        "right": [
                            {
                                "type": "gallery",
                                "settings": {
                                    "layout": "grid",
                                    "images": [_picsum("aurora-gallery-1", 800, 800), _picsum("aurora-gallery-2", 800, 800)],
                                },
                            },
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "settings": {
                        "title": "Loved by our customers",
                        "items": [
                            {"quote": "The quality is unreal for the price. My new go-to store.", "author": "Maya R.", "role": "Verified buyer"},
                            {"quote": "Fast shipping and the packaging alone felt premium.", "author": "Daniel K.", "role": "Verified buyer"},
                            {"quote": "Customer support actually helped me pick the right size.", "author": "Sarah L.", "role": "Verified buyer"},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [
                            {"label": "Shop the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}},
                            {"label": "Our story", "variant": "outline", "actionType": "NAVIGATE", "actionPayload": {"page_key": "about"}},
                        ]
                    },
                },
            ],
        },
        "about": {
            "title": "About",
            "background_color": "#faf8f5",
            "text_color": "#1f2937",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {"headline": "About us", "size": "small", "alignment": "center", "background_color": "#f1ede7"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "neutral"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "How it started",
                                    "body": (
                                        "We opened our doors because we couldn't find what we wanted to buy "
                                        "ourselves — thoughtfully designed, well made, and priced fairly. "
                                        "Today every product is still picked (or made) by our small team, one "
                                        "collection at a time."
                                    ),
                                },
                            },
                        ],
                        "right": [
                            {"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("aurora-about-1", 800, 800)]}},
                        ],
                    },
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "What we care about",
                        "items": [
                            {"icon": "Leaf", "title": "Sustainability", "text": "Responsibly sourced materials wherever we can."},
                            {"icon": "Award", "title": "Craftsmanship", "text": "Small batches, checked by hand."},
                            {"icon": "Heart", "title": "Community", "text": "A portion of every sale supports local makers."},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [{"label": "Shop the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]
                    },
                },
            ],
        },
        "contact": {
            "title": "Contact",
            "background_color": "#faf8f5",
            "text_color": "#1f2937",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {"headline": "Get in touch", "size": "small", "alignment": "center", "background_color": "#f1ede7"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "neutral"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "We'd love to hear from you",
                                    "body": "Email hello@yourstore.com and we'll get back to you within one business day.",
                                },
                            },
                        ],
                        "right": [
                            {
                                "type": "table",
                                "settings": {
                                    "title": "Support hours",
                                    "headers": ["Day", "Hours"],
                                    "rows": [["Mon – Fri", "9:00 – 18:00"], ["Saturday", "10:00 – 16:00"], ["Sunday", "Closed"]],
                                },
                            },
                        ],
                    },
                },
            ],
        },
    },
}

ATELIER: StorefrontTemplate = {
    "key": "atelier",
    "name": "Atelier",
    "tagline": "Dark, editorial, high-fashion.",
    "swatch": {"bg": "#15130f", "text": "#f5f0e6", "accent": "#c9a24b"},
    "pages": {
        "home": {
            "title": "Home",
            "background_color": "#15130f",
            "text_color": "#f5f0e6",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {
                        "headline": "Crafted for those who notice the details",
                        "size": "large",
                        "alignment": "left",
                        "background_color": "#1f1c16",
                        "text_color": "#f5f0e6",
                    },
                    "media": {"type": "image", "url": _picsum("atelier-hero"), "aspect_ratio": "16/9"},
                },
                {
                    "type": "product_grid",
                    "settings": {"title": "Bestsellers", "columns": 3, "card_style": "framed"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "secondary"},
                    "zones": {
                        "left": [
                            {"type": "gallery", "settings": {"layout": "carousel", "images": [_picsum("atelier-gallery-1", 900, 900), _picsum("atelier-gallery-2", 900, 900), _picsum("atelier-gallery-3", 900, 900)]}},
                        ],
                        "right": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "The atelier",
                                    "body": (
                                        "Every collection begins on a workbench, not a spreadsheet. We work in "
                                        "small runs with artisans we've partnered with for years, so every "
                                        "piece carries a little more weight than the price tag suggests."
                                    ),
                                    "background_color": "#1f1c16",
                                    "text_color": "#f5f0e6",
                                },
                            },
                        ],
                    },
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "The Atelier promise",
                        "items": [
                            {"icon": "Award", "title": "Limited runs", "text": "Small batches, never mass-produced."},
                            {"icon": "PackageCheck", "title": "Gift-ready packaging", "text": "Every order arrives ready to give."},
                            {"icon": "Headphones", "title": "Personal styling", "text": "Message us for one-to-one advice."},
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "settings": {
                        "title": "In their words",
                        "items": [
                            {"quote": "Feels like a piece I'll still be wearing in ten years.", "author": "Noa B.", "role": "Verified buyer"},
                            {"quote": "The packaging alone made it feel like an occasion.", "author": "Itay G.", "role": "Verified buyer"},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "background_color": "#1f1c16",
                        "buttons": [
                            {"label": "Explore the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}},
                        ],
                    },
                },
            ],
        },
        "about": {
            "title": "About",
            "background_color": "#15130f",
            "text_color": "#f5f0e6",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "About the atelier", "size": "small", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}},
                {
                    "type": "text_block",
                    "settings": {
                        "heading": "A house built on craft",
                        "body": (
                            "Founded by a small group of designers who wanted to slow things down, we work "
                            "directly with artisan workshops instead of factories. It costs more and takes "
                            "longer — we think that's the point."
                        ),
                        "background_color": "#1f1c16",
                        "text_color": "#f5f0e6",
                    },
                },
                {"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("atelier-about-1", 800, 800), _picsum("atelier-about-2", 800, 800)]}},
                {
                    "type": "button_group",
                    "settings": {
                        "background_color": "#1f1c16",
                        "buttons": [{"label": "Explore the collection", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}],
                    },
                },
            ],
        },
        "contact": {
            "title": "Contact",
            "background_color": "#15130f",
            "text_color": "#f5f0e6",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "Contact the atelier", "size": "small", "alignment": "left", "background_color": "#1f1c16", "text_color": "#f5f0e6"}},
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "secondary"},
                    "zones": {
                        "left": [{"type": "text_block", "settings": {"heading": "Reach us", "body": "hello@yourstore.com — private styling appointments available on request.", "background_color": "#1f1c16", "text_color": "#f5f0e6"}}],
                        "right": [{"type": "table", "settings": {"title": "Studio hours", "headers": ["Day", "Hours"], "rows": [["Tue – Sat", "11:00 – 19:00"], ["Sun – Mon", "By appointment"]]}}],
                    },
                },
            ],
        },
    },
}

NOVA: StorefrontTemplate = {
    "key": "nova",
    "name": "Nova",
    "tagline": "Bold, vivid, modern.",
    "swatch": {"bg": "#ffffff", "text": "#111827", "accent": "#f0653a"},
    "pages": {
        "home": {
            "title": "Home",
            "background_color": "#ffffff",
            "text_color": "#111827",
            "sections": [
                {
                    "type": "hero_banner",
                    "settings": {
                        "headline": "Everyday gear, leveled up",
                        "size": "large",
                        "alignment": "center",
                        "background_color": "#fff1ec",
                        "text_color": "#111827",
                    },
                    "media": {"type": "image", "url": _picsum("nova-hero"), "aspect_ratio": "16/9"},
                },
                {
                    "type": "feature_highlights",
                    "settings": {
                        "title": "Why you'll love it here",
                        "items": [
                            {"icon": "Truck", "title": "Fast shipping", "text": "Most orders ship within 24 hours."},
                            {"icon": "CreditCard", "title": "Flexible payment", "text": "Pay in full or split it up."},
                            {"icon": "Sparkles", "title": "New drops weekly", "text": "Fresh product every single week."},
                        ],
                    },
                },
                {
                    "type": "product_grid",
                    "settings": {"title": "Trending now", "columns": 4, "card_style": "default"},
                },
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "accent"},
                    "zones": {
                        "left": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "Built different",
                                    "body": "We obsess over the details other stores skip — real materials, real testing, real reviews.",
                                },
                            },
                        ],
                        "right": [
                            {"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("nova-gallery-1", 800, 800), _picsum("nova-gallery-2", 800, 800)]}},
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "settings": {
                        "title": "What people say",
                        "items": [
                            {"quote": "Ordered on Monday, wearing it by Wednesday. Insane.", "author": "Tom H.", "role": "Verified buyer"},
                            {"quote": "Finally a store that doesn't feel like every other store.", "author": "Priya S.", "role": "Verified buyer"},
                            {"quote": "The quality shocked me for this price point.", "author": "Alex M.", "role": "Verified buyer"},
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [
                            {"label": "Shop now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}},
                            {"label": "About us", "variant": "outline", "actionType": "NAVIGATE", "actionPayload": {"page_key": "about"}},
                        ]
                    },
                },
            ],
        },
        "about": {
            "title": "About",
            "background_color": "#ffffff",
            "text_color": "#111827",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "About us", "size": "small", "alignment": "center", "background_color": "#fff1ec"}},
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "muted"},
                    "zones": {
                        "left": [{"type": "gallery", "settings": {"layout": "grid", "images": [_picsum("nova-about-1", 800, 800)]}}],
                        "right": [
                            {
                                "type": "text_block",
                                "settings": {
                                    "heading": "Why we exist",
                                    "body": "We got tired of choosing between good design and a fair price — so we built a store that doesn't make you choose.",
                                },
                            },
                        ],
                    },
                },
                {
                    "type": "button_group",
                    "settings": {"buttons": [{"label": "Shop now", "variant": "primary", "actionType": "NAVIGATE", "actionPayload": {"page_key": "shop"}}]},
                },
            ],
        },
        "contact": {
            "title": "Contact",
            "background_color": "#ffffff",
            "text_color": "#111827",
            "sections": [
                {"type": "hero_banner", "settings": {"headline": "Talk to us", "size": "small", "alignment": "center", "background_color": "#fff1ec"}},
                {
                    "type": "two_column_layout",
                    "settings": {"design_variant": "muted"},
                    "zones": {
                        "left": [{"type": "text_block", "settings": {"heading": "Say hello", "body": "hello@yourstore.com — we usually reply the same day."}}],
                        "right": [{"type": "table", "settings": {"title": "Support hours", "headers": ["Day", "Hours"], "rows": [["Mon – Fri", "9:00 – 20:00"], ["Weekends", "10:00 – 15:00"]]}}],
                    },
                },
            ],
        },
    },
}

STOREFRONT_TEMPLATES: List[StorefrontTemplate] = [AURORA, ATELIER, NOVA]
STOREFRONT_TEMPLATES_BY_KEY: Dict[str, StorefrontTemplate] = {t["key"]: t for t in STOREFRONT_TEMPLATES}


def list_storefront_template_metas() -> List[StorefrontTemplateMeta]:
    return [{"key": t["key"], "name": t["name"], "tagline": t["tagline"], "swatch": t["swatch"]} for t in STOREFRONT_TEMPLATES]


def get_storefront_template(template_key: str) -> StorefrontTemplate | None:
    return STOREFRONT_TEMPLATES_BY_KEY.get(template_key)
