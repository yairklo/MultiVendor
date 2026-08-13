import json
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.catalog_schemas import ProductCreateRequest, ProductUpdateRequest, ProductVariantSchema
from app.schemas.order_schemas import CouponCreateRequest
from app.schemas.ai_schemas import PendingConfirmation
from app.services import ai_pending_action_service, catalog_service, coupon_service, order_service, store_page_service, tenant_service
from app.services.storefront_templates import get_storefront_template


# Caps on list-shaped tool outputs — a tenant can have thousands of orders/
# coupons, and dumping all of them into the model's context is both wasteful
# and a real risk of blowing the context window, so every listing tool clamps
# its result server-side rather than trusting the model to ask nicely.
DEFAULT_LIST_ORDERS_LIMIT = 20
MAX_LIST_ORDERS_LIMIT = 50
MAX_LIST_COUPONS_LIMIT = 50


class UngroundedReferenceError(ValueError):
    """Raised when a write tool references an entity id the model never verified via a read/list/create tool this turn."""


class ToolGroundingContext:
    """
    Tracks which real entity ids this single agent turn has actually observed
    via a successful read/list/create tool call, so a write tool (update/
    archive/delete/toggle) can refuse an id the model never verified instead
    of silently acting on a guessed or hallucinated one. Create one fresh per
    run_agent_turn call — never persisted across turns, since a store's data
    (and therefore which ids are real) can change between them.
    """

    ENTITY_TYPES = ("product", "variant", "coupon", "order")

    def __init__(self) -> None:
        self._seen: Dict[str, Set[int]] = {t: set() for t in self.ENTITY_TYPES}

    def mark(self, entity_type: str, entity_id: Any) -> None:
        if entity_id is None:
            return
        try:
            self._seen[entity_type].add(int(entity_id))
        except (TypeError, ValueError):
            pass

    def is_grounded(self, entity_type: str, entity_id: Any) -> bool:
        try:
            return int(entity_id) in self._seen[entity_type]
        except (TypeError, ValueError):
            return False


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

def _resolve_product_display_name(name: Any) -> str:
    if isinstance(name, dict):
        return name.get("en") or name.get("he") or next(iter(name.values()), "")
    return str(name)


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

    `delete_product`, `update_order_status` (when cancelling), and
    `update_page_sections` (when it would wipe most/all of an existing page's
    content) never perform the real action here — they stage an
    AIPendingAction and return a pending_confirmation instead; only a human
    clicking Confirm in the UI (ai_pending_action_service.confirm_pending_action_service,
    reached through the same tenant-admin-gated endpoint as everything else)
    actually runs them.
    """
    try:
        if tool_name == "list_page_targets":
            targets = await store_page_service.list_page_targets_service(tenant_slug, db)
            return ToolExecutionResult(tool_name, [t.model_dump(mode="json") for t in targets], False)

        if tool_name == "list_categories":
            categories = await catalog_service.list_public_categories_service(tenant_slug, db)
            return ToolExecutionResult(tool_name, [c.model_dump(mode="json") for c in categories], False)

        if tool_name == "get_page_schema":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            if not page_key or page_type not in ("static_page", "template"):
                raise ValueError("page_key and a valid page_type are required")
            schema = await store_page_service.get_page_schema_service(tenant_slug, page_key, page_type, db)
            return ToolExecutionResult(tool_name, schema.model_dump(mode="json"), False)

        if tool_name == "update_page_sections":
            page_key = raw_input.get("page_key")
            page_type = raw_input.get("page_type")
            sections = raw_input.get("sections")
            if not page_key or page_type not in ("static_page", "template") or not isinstance(sections, list):
                raise ValueError("page_key, page_type, and a sections array are required")

            # A brand-new page (404) is never gated — there's nothing to wipe.
            # An existing page with real content that this edit would reduce to
            # <=20% of its current sections (covers the "sections: []" wipe and
            # near-wipes) is staged instead of applied, same as delete_product.
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
            return ToolExecutionResult(tool_name, schema.model_dump(mode="json"), False)

        if tool_name == "create_product":
            req = ProductCreateRequest(
                category_id=raw_input.get("category_id"),
                name=raw_input.get("name") or {},
                slug=raw_input.get("slug", ""),
                description=raw_input.get("description"),
                base_price=raw_input.get("base_price"),
                variants=raw_input.get("variants") or [],
                images=raw_input.get("images") or [],
            )
            product = await catalog_service.create_product_service(tenant_slug, req, db)
            if context:
                context.mark("product", product.id)
                for v in product.variants:
                    context.mark("variant", v.id)
            return ToolExecutionResult(tool_name, product.model_dump(mode="json"), False)

        # --- Storefront templates -------------------------------------------
        if tool_name == "list_storefront_templates":
            metas = await store_page_service.list_storefront_templates_service()
            return ToolExecutionResult(tool_name, list(metas), False)

        if tool_name == "apply_storefront_template":
            template_key = raw_input.get("template_key")
            if not template_key:
                raise ValueError("template_key is required")
            template = get_storefront_template(template_key)
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

        # --- Catalog & inventory -------------------------------------------
        if tool_name == "get_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            product = await catalog_service.get_admin_product_service(tenant_slug, int(product_id), db)
            if context:
                context.mark("product", product.id)
                for v in product.variants:
                    context.mark("variant", v.id)
            return ToolExecutionResult(tool_name, product.model_dump(mode="json"), False)

        if tool_name == "update_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "get_product")
            fields = {k: v for k, v in raw_input.items() if k != "product_id"}
            req = ProductUpdateRequest(**fields)
            product = await catalog_service.update_product_service(tenant_slug, int(product_id), req, db)
            return ToolExecutionResult(tool_name, product.model_dump(mode="json"), False)

        if tool_name == "archive_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "get_product")
            product = await catalog_service.update_product_service(
                tenant_slug, int(product_id), ProductUpdateRequest(is_active=False), db
            )
            return ToolExecutionResult(tool_name, product.model_dump(mode="json"), False)

        if tool_name == "delete_product":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "get_product")
            # Only reads the product (to build a clear summary) — never deletes here.
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
            _require_grounded(context, "variant", variant_id, "get_product or get_inventory_health")
            current = await catalog_service.get_variant_service(tenant_slug, int(variant_id), db)
            merged = ProductVariantSchema(
                id=current.id, sku=current.sku, attributes_json=current.attributes_json,
                price_override=current.price_override, stock_quantity=int(stock_quantity),
            )
            updated = await catalog_service.update_product_variant_service(tenant_slug, int(variant_id), merged, db)
            return ToolExecutionResult(tool_name, updated.model_dump(mode="json"), False)

        if tool_name == "add_product_variant":
            product_id = raw_input.get("product_id")
            if product_id is None:
                raise ValueError("product_id is required")
            _require_grounded(context, "product", product_id, "get_product")
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
            return ToolExecutionResult(tool_name, variant.model_dump(mode="json"), False)

        # --- Coupons ---------------------------------------------------------
        if tool_name == "create_coupon":
            req = CouponCreateRequest(
                code=raw_input.get("code", ""),
                discount_type=raw_input.get("discount_type"),
                discount_val=raw_input.get("discount_val"),
                min_order_amt=raw_input.get("min_order_amt", 0),
                usage_limit=raw_input.get("usage_limit", 100),
                valid_until=raw_input.get("valid_until"),
            )
            coupon = await coupon_service.create_tenant_coupon_service(tenant_slug, req, db)
            if context:
                context.mark("coupon", coupon.id)
            return ToolExecutionResult(tool_name, coupon.model_dump(mode="json"), False)

        if tool_name == "list_coupons":
            coupons = await coupon_service.list_tenant_coupons_service(tenant_slug, db)
            if context:
                for c in coupons:
                    context.mark("coupon", c.id)
            return ToolExecutionResult(
                tool_name, [c.model_dump(mode="json") for c in coupons[:MAX_LIST_COUPONS_LIMIT]], False
            )

        if tool_name == "toggle_coupon_status":
            coupon_id = raw_input.get("coupon_id")
            is_active = raw_input.get("is_active")
            if coupon_id is None or is_active is None:
                raise ValueError("coupon_id and is_active are required")
            _require_grounded(context, "coupon", coupon_id, "list_coupons")
            coupon = await coupon_service.toggle_coupon_status_service(tenant_slug, int(coupon_id), bool(is_active), db)
            return ToolExecutionResult(tool_name, coupon.model_dump(mode="json"), False)

        # --- Orders ------------------------------------------------------------
        if tool_name == "list_orders":
            from datetime import datetime as _dt

            def _parse(v):
                return _dt.fromisoformat(v.replace("Z", "+00:00")) if v else None

            # A tenant can accumulate thousands of orders — never let the model pull
            # an unbounded result set into its own context window. Whatever it asks
            # for (or nothing at all) is clamped into a sane range server-side.
            requested_limit = raw_input.get("limit")
            try:
                limit = int(requested_limit) if requested_limit is not None else DEFAULT_LIST_ORDERS_LIMIT
            except (TypeError, ValueError):
                limit = DEFAULT_LIST_ORDERS_LIMIT
            limit = max(1, min(limit, MAX_LIST_ORDERS_LIMIT))

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
            return ToolExecutionResult(tool_name, [o.model_dump(mode="json") for o in orders], False)

        if tool_name == "get_order_details":
            order_id = raw_input.get("order_id")
            if order_id is None:
                raise ValueError("order_id is required")
            order = await order_service.get_tenant_order_service(tenant_slug, int(order_id), db)
            if context:
                context.mark("order", order.id)
            return ToolExecutionResult(tool_name, order.model_dump(mode="json"), False)

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

        # --- Analytics (read-only) -----------------------------------------------
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
                "top_selling_products": [p.model_dump(mode="json") for p in top_sellers],
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
            return ToolExecutionResult(tool_name, health.model_dump(mode="json"), False)

        return ToolExecutionResult(tool_name, {"error": f"Unknown tool: {tool_name}"}, True, error_type="UnknownTool")
    except UngroundedReferenceError as exc:
        return ToolExecutionResult(tool_name, {"error": str(exc)}, True, error_type="UngroundedReference")
    except HTTPException as exc:
        if exc.status_code >= 500:
            raise
        return ToolExecutionResult(
            tool_name, {"error": exc.detail}, True, error_type="NotFound" if exc.status_code == 404 else "ExecutionFailed"
        )
    except ValidationError as exc:
        # exc.errors() embeds raw, non-JSON-safe values (e.g. a Decimal in a numeric
        # constraint's ctx) — round-trip through exc.json() instead so this is safe to
        # persist (chat transcript, Gemini function-response history) as well as return.
        return ToolExecutionResult(tool_name, {"error": json.loads(exc.json())}, True, error_type="ValidationFailed")
    except ValueError as exc:
        return ToolExecutionResult(tool_name, {"error": str(exc)}, True, error_type="ValidationFailed")
