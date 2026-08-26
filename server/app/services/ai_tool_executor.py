import json
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.schemas.catalog_schemas import (
    CategoryCreateRequest, CategoryUpdateRequest, ProductCreateRequest, ProductUpdateRequest, ProductVariantSchema,
)
from app.schemas.order_schemas import CouponCreateRequest, CouponUpdateRequest
from app.schemas.tenant_schemas import TenantSettingsUpdateSchema
from app.schemas.ai_schemas import PendingConfirmation
from app.services import (
    ai_pending_action_service, catalog_service, coupon_service, import_service, order_service,
    shipping_service, store_page_service, tenant_service,
)
from app.services.ai_tools import ai_tools
from app.services.storefront_templates import get_storefront_template


# Caps on list-shaped tool outputs — a tenant can have thousands of orders/
# coupons, and dumping all of them into the model's context is both wasteful
# and a real risk of blowing the context window, so every listing tool clamps
# its result server-side rather than trusting the model to ask nicely.
DEFAULT_LIST_ORDERS_LIMIT = 20
MAX_LIST_ORDERS_LIMIT = 50
MAX_LIST_COUPONS_LIMIT = 50
DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 50

_IGNORED_TENANT_KEYS = frozenset({"tenant_id", "tenant_slug", "vendor_id", "vendor_slug"})
TOOL_PROPERTIES: Dict[str, Set[str]] = {
    t["name"]: set((t["parameters"] or {}).get("properties", {}).keys())
    for t in ai_tools
}

READ_TOOLS = frozenset({
    "list_page_targets", "list_categories", "get_page_schema", "list_storefront_templates",
    "list_products", "get_product", "list_coupons", "list_orders", "get_order_details",
    "get_sales_analytics", "get_customer_insights", "get_inventory_health",
    "list_reviews", "list_customers", "get_store_settings", "list_page_versions",
    "list_shipping_configs", "export_orders_csv",
})
WRITE_TOOLS = frozenset({
    "update_page_sections", "create_product", "bulk_import_products", "apply_storefront_template",
    "update_product", "archive_product", "delete_product", "update_inventory", "add_product_variant",
    "update_variant", "create_category", "update_category", "delete_category",
    "create_coupon", "toggle_coupon_status", "update_coupon", "delete_coupon",
    "update_order_status", "fulfill_order",
    "set_review_status", "update_store_settings", "publish_page", "revert_page_version",
    "delete_shipping_config", "upgrade_subscription",
})


class UngroundedReferenceError(ValueError):
    """Raised when a write tool references an entity id the model never verified via a read/list/create tool this conversation."""


class ToolGroundingContext:
    """
    Tracks which real entity ids this conversation has actually observed
    via a successful read/list/create tool call, so a write tool (update/
    archive/delete/toggle) can refuse an id the model never verified instead
    of silently acting on a guessed or hallucinated one.
    """

    ENTITY_TYPES = ("product", "variant", "coupon", "order", "category", "review", "page_version")
    STRING_ENTITY_TYPES = ("page_key", "shipping_provider")

    def __init__(self) -> None:
        self._seen: Dict[str, Set[int]] = {t: set() for t in self.ENTITY_TYPES}
        self._seen_str: Dict[str, Set[str]] = {t: set() for t in self.STRING_ENTITY_TYPES}

    def mark(self, entity_type: str, entity_id: Any) -> None:
        if entity_id is None:
            return
        try:
            self._seen[entity_type].add(int(entity_id))
        except (TypeError, ValueError, KeyError):
            pass

    def mark_str(self, entity_type: str, value: Any) -> None:
        if value is None or value == "":
            return
        try:
            self._seen_str[entity_type].add(str(value))
        except KeyError:
            pass

    def is_grounded(self, entity_type: str, entity_id: Any) -> bool:
        try:
            return int(entity_id) in self._seen[entity_type]
        except (TypeError, ValueError, KeyError):
            return False

    def is_grounded_str(self, entity_type: str, value: Any) -> bool:
        try:
            return str(value) in self._seen_str[entity_type]
        except KeyError:
            return False

    def seed_from_tool_output(self, tool_name: str, output: Any) -> None:
        """Re-ground ids that a prior successful tool call in this conversation already returned."""
        if output is None:
            return
        if tool_name in ("list_page_targets", "get_page_schema", "update_page_sections", "publish_page"):
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict) and item.get("page_key"):
                        self.mark_str("page_key", item["page_key"])
            elif isinstance(output, dict) and output.get("page_key"):
                self.mark_str("page_key", output["page_key"])
        self._seed_tree(output)

    def _seed_tree(self, output: Any) -> None:
        if isinstance(output, list):
            for item in output:
                self._seed_tree(item)
            return
        if not isinstance(output, dict):
            return
        if "product_id" in output:
            self.mark("product", output.get("product_id"))
        if "variant_id" in output:
            self.mark("variant", output.get("variant_id"))
        if "coupon_id" in output:
            self.mark("coupon", output.get("coupon_id"))
        if "order_id" in output:
            self.mark("order", output.get("order_id"))
        if "category_id" in output:
            self.mark("category", output.get("category_id"))
        if "review_id" in output:
            self.mark("review", output.get("review_id"))
        if "version_id" in output:
            self.mark("page_version", output.get("version_id"))
        if output.get("provider") and "is_default" in output:
            self.mark_str("shipping_provider", output.get("provider"))
        if "page_key" in output:
            self.mark_str("page_key", output.get("page_key"))
        # Typical entity payloads use `id` plus a discriminating sibling field.
        if "id" in output:
            if "sku" in output and "stock_quantity" in output and "slug" not in output:
                self.mark("variant", output["id"])
            elif "slug" in output and "base_price" in output:
                self.mark("product", output["id"])
            elif "slug" in output and "parent_id" in output:
                self.mark("category", output["id"])
            elif "discount_type" in output or "discount_val" in output:
                self.mark("coupon", output["id"])
            elif "order_number" in output:
                self.mark("order", output["id"])
            elif "rating" in output and "product_id" in output:
                self.mark("review", output["id"])
            elif "section_count" in output and "title" in output and "page_key" not in output:
                self.mark("page_version", output["id"])
        for key in ("variants", "created", "updated", "data", "out_of_stock", "low_stock", "items"):
            nested = output.get(key)
            if nested is not None:
                self._seed_tree(nested)


def _require_grounded(
    context: Optional[ToolGroundingContext], entity_type: str, entity_id: Any, lookup_hint: str
) -> None:
    """No-op when no context is supplied (e.g. direct unit-test calls to execute_tool) — grounding is
    enforced only for real agent-driven turns, which always pass one in."""
    if context is None:
        return
    if not context.is_grounded(entity_type, entity_id):
        raise UngroundedReferenceError(
            f"{entity_type}_id {entity_id!r} has not been verified in this conversation. Call {lookup_hint} "
            f"first to retrieve the real, current {entity_type}_id from the database — never guess or reuse "
            f"an id you haven't just looked up."
        )


def _require_grounded_str(
    context: Optional[ToolGroundingContext], entity_type: str, value: Any, lookup_hint: str
) -> None:
    if context is None:
        return
    if not context.is_grounded_str(entity_type, value):
        raise UngroundedReferenceError(
            f"{entity_type} {value!r} has not been verified in this conversation. Call {lookup_hint} first."
        )


def _reject_unknown_fields(tool_name: str, raw_input: Dict[str, Any]) -> None:
    allowed = TOOL_PROPERTIES.get(tool_name)
    if allowed is None:
        return
    unknown = set(raw_input) - allowed
    if unknown:
        raise ValueError(
            f"Unknown field(s) for {tool_name}: {', '.join(sorted(unknown))}. "
            "These cannot be handled — refusing a silent partial write."
        )


def _as_bool(value: Any, default: bool = False) -> bool:
    """Coerce JSON/tool-call booleans so the string \"false\" is not treated as True."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no", ""):
            return False
    return bool(value)


def _clamp_limit(raw_value: Any, default: int = DEFAULT_LIST_LIMIT, maximum: int = MAX_LIST_LIMIT) -> int:
    try:
        limit = int(raw_value) if raw_value is not None else default
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, maximum))


def _resolve_product_display_name(name: Any) -> str:
    if isinstance(name, dict):
        return name.get("en") or name.get("he") or next(iter(name.values()), "")
    return str(name)


def _dump(model: Any) -> Any:
    return model.model_dump(mode="json")


class ToolExecutionResult:
    def __init__(
        self,
        tool_name: str,
        output: Any,
        is_error: bool,
        pending_confirmation: Optional[PendingConfirmation] = None,
        error_type: Optional[str] = None,
    ):
        self.tool_name = tool_name
        self.output = output
        self.is_error = is_error
        self.pending_confirmation = pending_confirmation
        # Machine-readable failure category the agent loop uses to label the error back to the model —
        # "ValidationFailed" (bad/missing args), "UngroundedReference" (an id the model never verified),
        # "NotFound", or "ExecutionFailed" (default fallback).
        self.error_type = error_type or ("ExecutionFailed" if is_error else None)


def _mark_product(context: Optional[ToolGroundingContext], product: Any) -> None:
    if not context:
        return
    context.mark("product", product.id)
    for v in getattr(product, "variants", []) or []:
        context.mark("variant", getattr(v, "id", None) if not isinstance(v, dict) else v.get("id"))


async def execute_tool(
    tool_name: str, raw_input: Dict[str, Any], tenant_slug: str, db: AsyncSession,
    context: Optional[ToolGroundingContext] = None,
) -> ToolExecutionResult:
    """
    Executes a single tool call by name, always scoped to `tenant_slug` — the
    tenant bound server-side from the authenticated admin's JWT, never from the
    model's own function-call arguments (any tenant/vendor-like field in
    `raw_input` is simply never read below). Errors are caught and returned as a
    structured tool result instead of propagating, so a single bad tool call
    surfaces to the agent loop (and the user) instead of crashing the chat turn.

    Destructive / live-publish tools never perform the real action here — they
    stage an AIPendingAction and return a pending_confirmation instead; only a
    human clicking Confirm in the UI actually runs them.
    """
    try:
        if tool_name not in TOOL_PROPERTIES:
            return ToolExecutionResult(tool_name, {"error": f"Unknown tool: {tool_name}"}, True, error_type="UnknownTool")
        raw_input = {
            k: v for k, v in dict(raw_input or {}).items() if k not in _IGNORED_TENANT_KEYS
        }
        _reject_unknown_fields(tool_name, raw_input)

        if tool_name == "list_page_targets":
            targets = await store_page_service.list_page_targets_service(tenant_slug, db)
            if context:
                for t in targets:
                    context.mark_str("page_key", t.page_key)
            return ToolExecutionResult(tool_name, [_dump(t) for t in targets], False)

        if tool_name == "list_categories":
            categories = await catalog_service.list_public_categories_service(tenant_slug, db)
            if context:
                for c in categories:
                    context.mark("category", c.id)
            return ToolExecutionResult(tool_name, [_dump(c) for c in categories], False)

        if tool_name == "create_category":
            req = CategoryCreateRequest(**raw_input)
            category = await catalog_service.create_category_service(tenant_slug, req, db)
            if context:
                context.mark("category", category.id)
            return ToolExecutionResult(tool_name, _dump(category), False)

        if tool_name == "update_category":
            category_id = raw_input.get("category_id")
            if category_id is None:
                raise ValueError("category_id is required")
            _require_grounded(context, "category", category_id, "list_categories")
            fields = {k: v for k, v in raw_input.items() if k != "category_id"}
            req = CategoryUpdateRequest(**fields)
            category = await catalog_service.update_category_service(tenant_slug, int(category_id), req, db)
            return ToolExecutionResult(tool_name, _dump(category), False)

        if tool_name == "delete_category":
            category_id = raw_input.get("category_id")
            if category_id is None:
                raise ValueError("category_id is required")
            _require_grounded(context, "category", category_id, "list_categories")
            categories = await catalog_service.list_public_categories_service(tenant_slug, db)
            match = next((c for c in categories if c.id == int(category_id)), None)
            if match is None:
                raise HTTPException(status_code=404, detail="Category not found")
            display_name = _resolve_product_display_name(match.name)
            summary = f"Permanently delete category \"{display_name}\" (id {category_id}). This cannot be undone."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "delete_category", {"category_id": int(category_id)}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "get_page_schema":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            if not page_key or page_type not in ("static_page", "template"):
                raise ValueError("page_key and a valid page_type are required")
            schema = await store_page_service.get_page_schema_service(tenant_slug, page_key, page_type, db)
            if context:
                context.mark_str("page_key", page_key)
            return ToolExecutionResult(tool_name, _dump(schema), False)

        if tool_name == "update_page_sections":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            sections = raw_input.get("sections")
            if not page_key or page_type not in ("static_page", "template") or not isinstance(sections, list):
                raise ValueError("page_key, page_type, and a sections array are required")

            existing_section_count = None
            try:
                existing = await store_page_service.get_page_schema_service(tenant_slug, page_key, page_type, db)
                existing_section_count = len(existing.sections)
            except HTTPException:
                pass

            if existing_section_count is not None and existing_section_count >= 3 and \
                    len(sections) <= existing_section_count * 0.2:
                summary = (
                    f"Replace \"{page_key}\"'s {existing_section_count} sections with {len(sections)} — this "
                    f"removes most of the page's current content."
                )
                pending = await ai_pending_action_service.create_pending_action_service(
                    tenant_slug, "update_page_sections", dict(raw_input), summary, db
                )
                return ToolExecutionResult(
                    tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
                )

            schema = await store_page_service.upsert_page_sections_service(
                tenant_slug, page_key, page_type, sections, db,
                background_color=raw_input.get("background_color"),
                text_color=raw_input.get("text_color"),
            )
            if context:
                context.mark_str("page_key", page_key)
            return ToolExecutionResult(tool_name, _dump(schema), False)

        if tool_name == "create_product":
            payload = dict(raw_input)
            payload.setdefault("images", [])
            req = ProductCreateRequest(**payload)
            product = await catalog_service.create_product_service(tenant_slug, req, db)
            _mark_product(context, product)
            return ToolExecutionResult(tool_name, _dump(product), False)

        if tool_name == "bulk_import_products":
            rows = raw_input.get("rows")
            if not isinstance(rows, list) or not rows:
                raise ValueError("rows must be a non-empty array")
            summary = await import_service.commit_products_import(
                tenant_slug, [{"row_number": i + 1, "data": row} for i, row in enumerate(rows)], db
            )
            if context:
                for entry in summary["created"]:
                    context.mark("product", entry["product_id"])
                for entry in summary["updated"]:
                    context.mark("variant", entry["variant_id"])
                    context.mark("product", entry.get("product_id"))
            return ToolExecutionResult(tool_name, summary, False)

        if tool_name == "list_storefront_templates":
            metas = await store_page_service.list_storefront_templates_service(db)
            return ToolExecutionResult(tool_name, list(metas), False)

        if tool_name == "apply_storefront_template":
            template_key = raw_input.get("template_key")
            if not template_key:
                raise ValueError("template_key is required")
            template = await get_storefront_template(template_key, db)
            if not template:
                raise ValueError(f"Unknown storefront template: {template_key}")
            summary = (
                f"Switch this store to the \"{template['name']}\" template — this replaces the current "
                f"home, about, and contact pages (including any of your own edits) and publishes them "
                f"immediately."
            )
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "apply_storefront_template", {"template_key": template_key}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "list_products":
            products = await catalog_service.list_admin_products_service(
                tenant_slug, db,
                query=raw_input.get("query"),
                include_inactive=_as_bool(raw_input.get("include_inactive")),
                category_id=int(raw_input["category_id"]) if raw_input.get("category_id") is not None else None,
                limit=_clamp_limit(raw_input.get("limit")),
            )
            if context:
                for p in products:
                    _mark_product(context, p)
                    if p.category_id is not None:
                        context.mark("category", p.category_id)
            return ToolExecutionResult(tool_name, [_dump(p) for p in products], False)

        if tool_name == "get_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            product = await catalog_service.get_admin_product_service(tenant_slug, int(product_id), db)
            _mark_product(context, product)
            return ToolExecutionResult(tool_name, _dump(product), False)

        if tool_name == "update_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "list_products or get_product")
            fields = {k: v for k, v in raw_input.items() if k != "product_id"}
            req = ProductUpdateRequest(**fields)
            product = await catalog_service.update_product_service(tenant_slug, int(product_id), req, db)
            return ToolExecutionResult(tool_name, _dump(product), False)

        if tool_name == "archive_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "list_products or get_product")
            product = await catalog_service.update_product_service(
                tenant_slug, int(product_id), ProductUpdateRequest(is_active=False), db
            )
            return ToolExecutionResult(tool_name, _dump(product), False)

        if tool_name == "delete_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "list_products or get_product")
            product = await catalog_service.get_admin_product_service(tenant_slug, int(product_id), db)
            display_name = _resolve_product_display_name(product.name)
            summary = f"Permanently delete product \"{display_name}\" (id {product_id}) and all its images/reviews/variants. This cannot be undone."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "delete_product", {"product_id": int(product_id)}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "update_inventory":
            variant_id = raw_input.get("variant_id")
            stock_quantity = raw_input.get("stock_quantity")
            if variant_id is None or stock_quantity is None:
                raise ValueError("variant_id and stock_quantity are required")
            _require_grounded(context, "variant", variant_id, "get_product or list_products")
            current = await catalog_service.get_variant_service(tenant_slug, int(variant_id), db)
            merged = ProductVariantSchema(
                id=current.id, sku=current.sku, attributes_json=current.attributes_json,
                price_override=current.price_override, stock_quantity=int(stock_quantity),
            )
            updated = await catalog_service.update_product_variant_service(tenant_slug, int(variant_id), merged, db)
            return ToolExecutionResult(tool_name, _dump(updated), False)

        if tool_name == "add_product_variant":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "list_products or get_product")
            attributes_json = raw_input.get("attributes_json") or {}
            if not isinstance(attributes_json, dict):
                raise ValueError("attributes_json must be an object, e.g. {\"color\": \"red\", \"size\": \"M\"}")
            req = ProductVariantSchema(
                sku=raw_input.get("sku", ""),
                attributes_json=attributes_json,
                price_override=raw_input.get("price_override"),
                stock_quantity=raw_input.get("stock_quantity", 0),
            )
            variant = await catalog_service.add_product_variant_service(tenant_slug, int(product_id), req, db)
            if context:
                context.mark("variant", variant.id)
            return ToolExecutionResult(tool_name, _dump(variant), False)

        if tool_name == "update_variant":
            variant_id = raw_input.get("variant_id")
            if variant_id is None:
                raise ValueError("variant_id is required")
            _require_grounded(context, "variant", variant_id, "get_product or list_products")
            current = await catalog_service.get_variant_service(tenant_slug, int(variant_id), db)
            attributes_json = raw_input["attributes_json"] if "attributes_json" in raw_input else current.attributes_json
            if attributes_json is not None and not isinstance(attributes_json, dict):
                raise ValueError("attributes_json must be an object, e.g. {\"color\": \"red\", \"size\": \"M\"}")
            merged = ProductVariantSchema(
                id=current.id,
                sku=raw_input["sku"] if "sku" in raw_input else current.sku,
                attributes_json=attributes_json or {},
                price_override=raw_input["price_override"] if "price_override" in raw_input else current.price_override,
                stock_quantity=int(raw_input["stock_quantity"]) if "stock_quantity" in raw_input else current.stock_quantity,
            )
            updated = await catalog_service.update_product_variant_service(tenant_slug, int(variant_id), merged, db)
            return ToolExecutionResult(tool_name, _dump(updated), False)

        if tool_name == "create_coupon":
            req = CouponCreateRequest(**raw_input)
            coupon = await coupon_service.create_tenant_coupon_service(tenant_slug, req, db)
            if context:
                context.mark("coupon", coupon.id)
            return ToolExecutionResult(tool_name, _dump(coupon), False)

        if tool_name == "list_coupons":
            coupons = await coupon_service.list_tenant_coupons_service(tenant_slug, db)
            if context:
                for c in coupons:
                    context.mark("coupon", c.id)
            return ToolExecutionResult(
                tool_name, [_dump(c) for c in coupons[:MAX_LIST_COUPONS_LIMIT]], False
            )

        if tool_name == "toggle_coupon_status":
            coupon_id = raw_input.get("coupon_id")
            is_active = raw_input.get("is_active")
            if coupon_id is None or is_active is None:
                raise ValueError("coupon_id and is_active are required")
            _require_grounded(context, "coupon", coupon_id, "list_coupons")
            coupon = await coupon_service.toggle_coupon_status_service(
                tenant_slug, int(coupon_id), _as_bool(is_active), db
            )
            return ToolExecutionResult(tool_name, _dump(coupon), False)

        if tool_name == "update_coupon":
            coupon_id = raw_input.get("coupon_id")
            if coupon_id is None:
                raise ValueError("coupon_id is required")
            _require_grounded(context, "coupon", coupon_id, "list_coupons")
            fields = {k: v for k, v in raw_input.items() if k != "coupon_id"}
            req = CouponUpdateRequest(**fields)
            coupon = await coupon_service.update_coupon_service(tenant_slug, int(coupon_id), req, db)
            return ToolExecutionResult(tool_name, _dump(coupon), False)

        if tool_name == "delete_coupon":
            coupon_id = raw_input.get("coupon_id")
            if coupon_id is None:
                raise ValueError("coupon_id is required")
            _require_grounded(context, "coupon", coupon_id, "list_coupons")
            coupons = await coupon_service.list_tenant_coupons_service(tenant_slug, db)
            match = next((c for c in coupons if c.id == int(coupon_id)), None)
            if match is None:
                raise HTTPException(status_code=404, detail="Coupon not found")
            summary = f"Permanently delete coupon \"{match.code}\" (id {coupon_id}). This cannot be undone."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "delete_coupon", {"coupon_id": int(coupon_id)}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "list_orders":
            from datetime import datetime as _dt

            def _parse(v):
                return _dt.fromisoformat(v.replace("Z", "+00:00")) if v else None

            limit = _clamp_limit(raw_input.get("limit"), DEFAULT_LIST_ORDERS_LIMIT, MAX_LIST_ORDERS_LIMIT)
            orders = await order_service.list_tenant_orders_service(
                tenant_slug, db,
                status=raw_input.get("status"),
                start_date=_parse(raw_input.get("start_date")),
                end_date=_parse(raw_input.get("end_date")),
                customer_email=raw_input.get("customer_email"),
                limit=limit,
            )
            if context:
                for o in orders:
                    context.mark("order", o.id)
            return ToolExecutionResult(tool_name, [_dump(o) for o in orders], False)

        if tool_name == "get_order_details":
            order_id = raw_input.get("order_id")
            if order_id is None:
                raise ValueError("order_id is required")
            order = await order_service.get_tenant_order_service(tenant_slug, int(order_id), db)
            if context:
                context.mark("order", order.id)
            return ToolExecutionResult(tool_name, _dump(order), False)

        if tool_name == "update_order_status":
            order_id = raw_input.get("order_id")
            status = raw_input.get("status")
            if order_id is None or status not in ("processing", "completed", "cancelled"):
                raise ValueError("order_id and a valid status are required")
            _require_grounded(context, "order", order_id, "list_orders or get_order_details")

            if status == "cancelled":
                order = await order_service.get_tenant_order_service(tenant_slug, int(order_id), db)
                summary = f"Cancel order {order.order_number} (${order.total_amount}) and restore its reserved stock. This cannot be easily undone."
                pending = await ai_pending_action_service.create_pending_action_service(
                    tenant_slug, "update_order_status", {"order_id": int(order_id), "status": "cancelled"}, summary, db
                )
                return ToolExecutionResult(
                    tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
                )

            result = await order_service.update_order_status_service(tenant_slug, int(order_id), status, db)
            return ToolExecutionResult(tool_name, result, False)

        if tool_name == "fulfill_order":
            order_id = raw_input.get("order_id")
            if order_id is None:
                raise ValueError("order_id is required")
            _require_grounded(context, "order", order_id, "list_orders or get_order_details")
            provider_override = raw_input.get("provider_override")
            if provider_override is not None and provider_override not in ("hfd", "lionwheel"):
                raise ValueError("provider_override must be 'hfd' or 'lionwheel'")
            order = await order_service.get_tenant_order_service(tenant_slug, int(order_id), db)
            if order.order_type == "digital":
                raise ValueError("Digital orders don't need a shipment")
            if order.status != "processing":
                raise ValueError(
                    f"Order must be 'processing' to fulfill (currently '{order.status}')"
                )
            courier = provider_override or "the store's default courier"
            summary = (
                f"Create a real shipment for order {order.order_number} via {courier}. "
                "This contacts HFD/Lionwheel and cannot be undone."
            )
            pending_args: Dict[str, Any] = {"order_id": int(order_id)}
            if provider_override:
                pending_args["provider_override"] = provider_override
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "fulfill_order", pending_args, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False,
                pending_confirmation=pending,
            )

        if tool_name == "export_orders_csv":
            summary = await catalog_service.summarize_orders_export_service(tenant_slug, db)
            return ToolExecutionResult(tool_name, summary, False)

        if tool_name == "get_sales_analytics":
            start_date = raw_input.get("start_date")
            end_date = raw_input.get("end_date")
            if not start_date or not end_date:
                raise ValueError("start_date and end_date are required")
            analytics = await tenant_service.get_tenant_analytics_service(tenant_slug, start_date, end_date, db)
            top_sellers = await tenant_service.get_top_selling_products_service(tenant_slug, start_date, end_date, db)
            output = {
                "start_date": start_date,
                "end_date": end_date,
                "total_revenue": analytics["total_revenue"],
                "orders_count": analytics["orders_count"],
                "aov": analytics["aov"],
                "daily": analytics["data"],
                "top_selling_products": [_dump(p) for p in top_sellers],
            }
            return ToolExecutionResult(tool_name, output, False)

        if tool_name == "get_customer_insights":
            insights = await order_service.get_customer_insights_service(tenant_slug, db)
            return ToolExecutionResult(tool_name, insights, False)

        if tool_name == "get_inventory_health":
            health = await catalog_service.get_inventory_health_service(tenant_slug, db)
            if context:
                for item in (*health.out_of_stock, *health.low_stock):
                    context.mark("product", item.product_id)
                    context.mark("variant", item.variant_id)
            return ToolExecutionResult(tool_name, _dump(health), False)

        if tool_name == "list_reviews":
            reviews = await catalog_service.list_tenant_reviews_service(tenant_slug, db)
            limit = _clamp_limit(raw_input.get("limit"))
            sliced = reviews[:limit]
            if context:
                for r in sliced:
                    context.mark("review", r.id)
            return ToolExecutionResult(tool_name, [_dump(r) for r in sliced], False)

        if tool_name == "set_review_status":
            review_id = raw_input.get("review_id")
            status = raw_input.get("status")
            if review_id is None or status not in ("approved", "rejected", "pending"):
                raise ValueError("review_id and a valid status (approved, rejected, pending) are required")
            _require_grounded(context, "review", review_id, "list_reviews")
            review = await catalog_service.update_review_status_service(tenant_slug, int(review_id), status, db)
            return ToolExecutionResult(tool_name, _dump(review), False)

        if tool_name == "list_customers":
            customers = await order_service.list_tenant_customers_service(tenant_slug, db)
            query = (raw_input.get("query") or "").strip().lower()
            if query:
                customers = [
                    c for c in customers
                    if query in (c.email or "").lower() or query in (c.full_name or "").lower()
                ]
            limit = _clamp_limit(raw_input.get("limit"))
            return ToolExecutionResult(tool_name, [_dump(c) for c in customers[:limit]], False)

        if tool_name == "get_store_settings":
            settings = await catalog_service.get_store_config_service(tenant_slug, db, admin_preview=True)
            tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
            tenant = tenant_result.scalar_one_or_none()
            output = _dump(settings)
            output["stripe_connect"] = {
                "is_connected": bool(tenant and tenant.stripe_account_id),
                "note": "Stripe Connect is a browser OAuth flow. Open Store Settings to connect or reconnect — the assistant cannot complete it.",
            }
            return ToolExecutionResult(tool_name, output, False)

        if tool_name == "update_store_settings":
            req = TenantSettingsUpdateSchema(**raw_input)
            settings = await tenant_service.update_store_settings_service(tenant_slug, req, db)
            return ToolExecutionResult(tool_name, _dump(settings), False)

        if tool_name == "list_page_versions":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            if not page_key or page_type not in ("static_page", "template"):
                raise ValueError("page_key and a valid page_type are required")
            versions = await store_page_service.list_page_versions_service(tenant_slug, page_key, page_type, db)
            if context:
                context.mark_str("page_key", page_key)
                for v in versions:
                    context.mark("page_version", v.id)
            return ToolExecutionResult(tool_name, [_dump(v) for v in versions], False)

        if tool_name == "publish_page":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            if not page_key or page_type not in ("static_page", "template"):
                raise ValueError("page_key and a valid page_type are required")
            _require_grounded_str(context, "page_key", page_key, "list_page_targets or get_page_schema")
            summary = f"Publish the current draft of \"{page_key}\" to the live storefront. This goes live immediately once confirmed."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "publish_page", {"page_key": page_key, "page_type": page_type}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "revert_page_version":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            version_id = raw_input.get("version_id")
            if not page_key or page_type not in ("static_page", "template") or version_id is None:
                raise ValueError("page_key, page_type, and version_id are required")
            _require_grounded_str(context, "page_key", page_key, "list_page_targets or get_page_schema")
            _require_grounded(context, "page_version", version_id, "list_page_versions")
            summary = f"Revert \"{page_key}\" to version {version_id}. The current draft will be snapshotted first."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "revert_page_version",
                {"page_key": page_key, "page_type": page_type, "version_id": int(version_id)},
                summary, db,
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "list_shipping_configs":
            configs = await shipping_service.list_tenant_shipping_configs_service(tenant_slug, db)
            if context:
                for c in configs:
                    context.mark_str("shipping_provider", c.provider)
            return ToolExecutionResult(tool_name, [_dump(c) for c in configs], False)

        if tool_name == "delete_shipping_config":
            provider = raw_input.get("provider")
            if provider not in ("hfd", "lionwheel"):
                raise ValueError("provider must be 'hfd' or 'lionwheel'")
            _require_grounded_str(context, "shipping_provider", provider, "list_shipping_configs")
            summary = f"Remove the \"{provider}\" shipping provider configuration from this store."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "delete_shipping_config", {"provider": provider}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        if tool_name == "upgrade_subscription":
            target_plan_code = raw_input.get("target_plan_code")
            if target_plan_code not in ("free", "pro", "enterprise"):
                raise ValueError("target_plan_code must be free, pro, or enterprise")
            summary = f"Upgrade this store's subscription to the \"{target_plan_code}\" plan."
            pending = await ai_pending_action_service.create_pending_action_service(
                tenant_slug, "upgrade_subscription", {"target_plan_code": target_plan_code}, summary, db
            )
            return ToolExecutionResult(
                tool_name, {"status": "confirmation_required", "summary": summary}, False, pending_confirmation=pending
            )

        return ToolExecutionResult(tool_name, {"error": f"Unknown tool: {tool_name}"}, True, error_type="UnknownTool")
    except UngroundedReferenceError as exc:
        return ToolExecutionResult(tool_name, {"error": str(exc)}, True, error_type="UngroundedReference")
    except HTTPException as exc:
        if exc.status_code >= 500:
            raise
        return ToolExecutionResult(
            tool_name, {"error": exc.detail}, True,
            error_type="NotFound" if exc.status_code == 404 else (
                "ValidationFailed" if exc.status_code == 422 else "ExecutionFailed"
            ),
        )
    except ValidationError as exc:
        # exc.errors() embeds raw, non-JSON-safe values (e.g. a Decimal in a numeric
        # constraint's ctx) — round-trip through exc.json() instead so this is safe to
        # persist (chat transcript, Gemini function-response history) as well as return.
        return ToolExecutionResult(tool_name, {"error": json.loads(exc.json())}, True, error_type="ValidationFailed")
    except ValueError as exc:
        return ToolExecutionResult(tool_name, {"error": str(exc)}, True, error_type="ValidationFailed")
