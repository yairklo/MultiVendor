from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.ai_pending_action import AIPendingAction
from app.models.order import Order
from app.models.tenant import Tenant
from app.services.ai_tool_executor import execute_tool, DEFAULT_LIST_ORDERS_LIMIT, MAX_LIST_ORDERS_LIMIT
from app.services import ai_pending_action_service
from app.services.checkout_service import validate_coupon_service
from app.services.ai_mock_agent import _format_markdown_table


# ---------------------------------------------------------------------------
# Catalog & inventory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_and_update_product_tools_are_scoped_to_tenant(db_session):
    get_result = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert get_result.is_error is False
    assert get_result.output["id"] == 1

    # tenant-b can't read tenant-a's product, even knowing its id.
    cross_tenant = await execute_tool("get_product", {"product_id": 1}, "tenant-b", db_session)
    assert cross_tenant.is_error is True

    update_result = await execute_tool(
        "update_product", {"product_id": 1, "base_price": 15.5}, "tenant-a", db_session
    )
    assert update_result.is_error is False
    assert float(update_result.output["base_price"]) == 15.5


@pytest.mark.asyncio
async def test_archive_product_deactivates_without_deleting(db_session):
    result = await execute_tool("archive_product", {"product_id": 1}, "tenant-a", db_session)
    assert result.is_error is False
    assert result.output["is_active"] is False

    # Still readable — archiving is a soft, reversible change, not a DELETE.
    still_there = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert still_there.is_error is False
    assert still_there.output["id"] == 1


@pytest.mark.asyncio
async def test_delete_product_only_stages_until_confirmed_and_is_tenant_scoped(db_session):
    # Calling the tool alone must NOT delete anything — it only stages the action.
    result = await execute_tool("delete_product", {"product_id": 1}, "tenant-a", db_session)
    assert result.is_error is False
    assert result.pending_confirmation is not None
    confirmation_id = result.pending_confirmation.id

    still_there = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert still_there.is_error is False

    # A different tenant can't confirm or cancel tenant-a's pending action.
    with pytest.raises(Exception):
        await ai_pending_action_service.confirm_pending_action_service("tenant-b", confirmation_id, db_session)
    with pytest.raises(Exception):
        await ai_pending_action_service.cancel_pending_action_service("tenant-b", confirmation_id, db_session)

    # The correct tenant confirming actually deletes it, and it's one-time use.
    await ai_pending_action_service.confirm_pending_action_service("tenant-a", confirmation_id, db_session)
    gone = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert gone.is_error is True

    with pytest.raises(Exception):
        await ai_pending_action_service.confirm_pending_action_service("tenant-a", confirmation_id, db_session)


@pytest.mark.asyncio
async def test_delete_product_pending_action_can_be_cancelled_without_executing(db_session):
    result = await execute_tool("delete_product", {"product_id": 1}, "tenant-a", db_session)
    confirmation_id = result.pending_confirmation.id

    await ai_pending_action_service.cancel_pending_action_service("tenant-a", confirmation_id, db_session)

    still_there = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert still_there.is_error is False

    remaining = (await db_session.execute(
        select(AIPendingAction).where(AIPendingAction.id == confirmation_id)
    )).scalar_one_or_none()
    assert remaining is None


@pytest.mark.asyncio
async def test_update_inventory_only_changes_stock_and_preserves_other_variant_fields(db_session):
    # Seeded variant id=1 (tenant-a, product 1): sku="SKU-A1-1", stock_quantity=10, no price_override.
    result = await execute_tool(
        "update_inventory", {"variant_id": 1, "stock_quantity": 42}, "tenant-a", db_session
    )
    assert result.is_error is False
    assert result.output["stock_quantity"] == 42
    assert result.output["sku"] == "SKU-A1-1"
    assert result.output["price_override"] is None


@pytest.mark.asyncio
async def test_add_product_variant_tool(db_session):
    result = await execute_tool(
        "add_product_variant",
        {"product_id": 1, "sku": "SKU-A1-2", "stock_quantity": 7, "attributes_json": {"color": "blue"}},
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.output["sku"] == "SKU-A1-2"
    assert result.output["stock_quantity"] == 7


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_list_and_toggle_coupon_tools(db_session):
    valid_until = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    create_result = await execute_tool(
        "create_coupon",
        {"code": "AICOUPON", "discount_type": "percentage", "discount_val": 15, "valid_until": valid_until},
        "tenant-a",
        db_session,
    )
    assert create_result.is_error is False
    coupon_id = create_result.output["id"]
    assert create_result.output["is_active"] is True

    list_result = await execute_tool("list_coupons", {}, "tenant-a", db_session)
    assert list_result.is_error is False
    assert any(c["id"] == coupon_id for c in list_result.output)

    toggle_result = await execute_tool(
        "toggle_coupon_status", {"coupon_id": coupon_id, "is_active": False}, "tenant-a", db_session
    )
    assert toggle_result.is_error is False
    assert toggle_result.output["is_active"] is False


@pytest.mark.asyncio
async def test_disabled_coupon_is_rejected_at_checkout(db_session):
    # Seeded coupon id=1 ("VALID10") for tenant-a starts active.
    valid_coupon = await validate_coupon_service("tenant-a", "VALID10", db_session)
    assert valid_coupon.code == "VALID10"

    toggle_result = await execute_tool(
        "toggle_coupon_status", {"coupon_id": 1, "is_active": False}, "tenant-a", db_session
    )
    assert toggle_result.is_error is False

    with pytest.raises(Exception) as exc_info:
        await validate_coupon_service("tenant-a", "VALID10", db_session)
    assert "disabled" in str(exc_info.value).lower() or getattr(exc_info.value, "detail", "") == "Coupon is disabled"


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orders_is_capped_even_when_the_store_has_many_orders(db_session):
    tenant_id = (await db_session.execute(select(Tenant.id).where(Tenant.slug == "tenant-a"))).scalar_one()
    for i in range(DEFAULT_LIST_ORDERS_LIMIT + 30):
        db_session.add(Order(
            tenant_id=tenant_id, user_id=4, order_number=f"ORD-BULK-{i}",
            subtotal=10, total_amount=10, status="completed",
        ))
    await db_session.commit()

    # No limit requested — falls back to the default cap, not every order.
    default_result = await execute_tool("list_orders", {}, "tenant-a", db_session)
    assert default_result.is_error is False
    assert len(default_result.output) == DEFAULT_LIST_ORDERS_LIMIT

    # A model asking for an enormous limit is still clamped to the hard max.
    oversized_result = await execute_tool("list_orders", {"limit": 999999}, "tenant-a", db_session)
    assert oversized_result.is_error is False
    assert len(oversized_result.output) == MAX_LIST_ORDERS_LIMIT


@pytest.mark.asyncio
async def test_add_product_variant_rejects_non_object_attributes_json(db_session):
    result = await execute_tool(
        "add_product_variant",
        {"product_id": 1, "sku": "SKU-BAD", "attributes_json": "not-an-object"},
        "tenant-a",
        db_session,
    )
    assert result.is_error is True
    assert "attributes_json" in result.output["error"]


def test_markdown_table_escapes_pipe_characters_in_cell_values():
    table = _format_markdown_table(["Name", "Stock"], [["Mug | Special Edition", 5]])
    data_row = table.splitlines()[2]
    # Exactly two real column separators (the leading/trailing edges) — the
    # pipe inside the product name must be escaped, not treated as a new column.
    assert data_row.count(" | ") == 1
    assert "Mug \\| Special Edition" in data_row


@pytest.mark.asyncio
async def test_list_orders_and_get_order_details_tools(db_session):
    list_result = await execute_tool("list_orders", {}, "tenant-a", db_session)
    assert list_result.is_error is False
    assert any(o["id"] == 1 for o in list_result.output)

    # tenant-b sees none of tenant-a's orders.
    cross_tenant_list = await execute_tool("list_orders", {}, "tenant-b", db_session)
    assert cross_tenant_list.is_error is False
    assert cross_tenant_list.output == []

    details_result = await execute_tool("get_order_details", {"order_id": 1}, "tenant-a", db_session)
    assert details_result.is_error is False
    assert details_result.output["id"] == 1

    cross_tenant_details = await execute_tool("get_order_details", {"order_id": 1}, "tenant-b", db_session)
    assert cross_tenant_details.is_error is True


@pytest.mark.asyncio
async def test_update_order_status_executes_directly_but_gates_cancellation(db_session):
    processing_result = await execute_tool(
        "update_order_status", {"order_id": 1, "status": "processing"}, "tenant-a", db_session
    )
    assert processing_result.is_error is False
    assert processing_result.pending_confirmation is None

    details = await execute_tool("get_order_details", {"order_id": 1}, "tenant-a", db_session)
    assert details.output["status"] == "processing"

    cancel_result = await execute_tool(
        "update_order_status", {"order_id": 1, "status": "cancelled"}, "tenant-a", db_session
    )
    assert cancel_result.is_error is False
    assert cancel_result.pending_confirmation is not None

    # Staging a cancellation must not have actually cancelled the order yet.
    details_after_stage = await execute_tool("get_order_details", {"order_id": 1}, "tenant-a", db_session)
    assert details_after_stage.output["status"] == "processing"

    await ai_pending_action_service.confirm_pending_action_service(
        "tenant-a", cancel_result.pending_confirmation.id, db_session
    )
    details_after_confirm = await execute_tool("get_order_details", {"order_id": 1}, "tenant-a", db_session)
    assert details_after_confirm.output["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Analytics (read-only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_sales_analytics_tool(db_session):
    # The seeded order starts as 'pending', which analytics deliberately excludes
    # (PAID_ORDER_STATUSES) — mark it paid first so it counts toward the totals.
    await execute_tool("update_order_status", {"order_id": 1, "status": "processing"}, "tenant-a", db_session)

    start = "2000-01-01T00:00:00Z"
    end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    result = await execute_tool(
        "get_sales_analytics", {"start_date": start, "end_date": end}, "tenant-a", db_session
    )
    assert result.is_error is False
    assert result.output["orders_count"] >= 1
    assert result.output["total_revenue"] >= 100.0
    assert "top_selling_products" in result.output


@pytest.mark.asyncio
async def test_get_customer_insights_tool(db_session):
    result = await execute_tool("get_customer_insights", {}, "tenant-a", db_session)
    assert result.is_error is False
    assert result.output["total_customers"] >= 1


@pytest.mark.asyncio
async def test_get_inventory_health_tool_buckets_by_stock_quantity(db_session):
    await execute_tool("update_inventory", {"variant_id": 1, "stock_quantity": 0}, "tenant-a", db_session)

    result = await execute_tool("get_inventory_health", {}, "tenant-a", db_session)
    assert result.is_error is False
    assert any(item["sku"] == "SKU-A1-1" for item in result.output["out_of_stock"])
    assert result.output["low_stock_threshold"] > 0


# ---------------------------------------------------------------------------
# Router-level: pending-action confirm/cancel endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pending_action_router_endpoints_are_tenant_scoped(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}

    # No pending action exists at all yet — confirm/cancel against an unknown
    # (or cross-tenant) id must 404, never leak whether the id belongs to someone else.
    random_id = "00000000-0000-0000-0000-000000000000"
    confirm_resp = await async_client.post(
        f"/api/v1/admin/store/tenant-a/ai/pending-actions/{random_id}/confirm", headers=headers_a
    )
    assert confirm_resp.status_code == 404

    cross_tenant_resp = await async_client.post(
        f"/api/v1/admin/store/tenant-b/ai/pending-actions/{random_id}/cancel", headers=headers_b
    )
    assert cross_tenant_resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_response_surfaces_pending_confirmation_end_to_end(async_client: AsyncClient, seed_tokens, db_session):
    # Stage a real pending delete via the tool layer, then confirm it through
    # the actual HTTP router endpoint the frontend's Confirm button calls.
    result = await execute_tool("delete_product", {"product_id": 1}, "tenant-a", db_session)
    confirmation_id = result.pending_confirmation.id

    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}

    # tenant-b cannot confirm tenant-a's staged deletion, even knowing its id.
    cross_tenant_confirm = await async_client.post(
        f"/api/v1/admin/store/tenant-b/ai/pending-actions/{confirmation_id}/confirm", headers=headers_b
    )
    assert cross_tenant_confirm.status_code == 404

    own_confirm = await async_client.post(
        f"/api/v1/admin/store/tenant-a/ai/pending-actions/{confirmation_id}/confirm", headers=headers_a
    )
    assert own_confirm.status_code == 200

    gone = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert gone.is_error is True
