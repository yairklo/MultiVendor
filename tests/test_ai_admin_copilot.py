from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.ai_pending_action import AIPendingAction
from app.models.order import Order
from app.models.tenant import Tenant, TenantSettings
from app.services.ai_tool_executor import execute_tool, DEFAULT_LIST_ORDERS_LIMIT, MAX_LIST_ORDERS_LIMIT
from app.services import ai_pending_action_service
from app.services.checkout_service import validate_coupon_service
from app.services.ai_mock_agent import _format_markdown_table
from app.services.storefront_templates import STOREFRONT_TEMPLATES
from app.schemas.ai_schemas import Section


# ---------------------------------------------------------------------------
# Catalog & inventory
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_and_update_product_tools_are_scoped_to_tenant(db_session):
    get_result = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    if get_result.is_error:
        print(get_result.output)
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
async def test_bulk_import_replaces_image_on_existing_sku(db_session):
    image_url = "https://images.example.com/mug.jpg"
    result = await execute_tool(
        "bulk_import_products",
        {
            "rows": [{
                "sku": "SKU-A1-1",
                "base_price": 10,
                "stock_quantity": 10,
                "image_url": image_url,
            }]
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.output["updated_count"] == 1
    assert result.output["created_count"] == 0
    assert result.output["updated"][0]["primary_image_url"] == image_url
    assert result.output["updated"][0]["product_id"] == 1

    product = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert product.is_error is False
    assert product.output["images"] == [image_url]
    assert product.output["primary_image_url"] == image_url


@pytest.mark.asyncio
async def test_bulk_import_updates_name_description_and_category_on_existing_sku(db_session):
    category = await execute_tool(
        "create_category",
        {"name": {"en": "Mugs", "he": "ספלים"}, "slug": "mugs"},
        "tenant-a",
        db_session,
    )
    assert category.is_error is False
    category_id = category.output["id"]

    result = await execute_tool(
        "bulk_import_products",
        {
            "rows": [{
                "sku": "SKU-A1-1",
                "base_price": 12,
                "stock_quantity": 8,
                "name_en": "Updated Mug",
                "name_he": "ספל מעודכן",
                "description_en": "A nicer mug",
                "category_id": category_id,
            }]
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.output["updated_count"] == 1
    assert result.output["failed_count"] == 0
    updated = result.output["updated"][0]
    assert updated["name"]["en"] == "Updated Mug"
    assert updated["description"]["en"] == "A nicer mug"
    assert updated["category_id"] == category_id

    product = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert product.output["name"]["en"] == "Updated Mug"
    assert product.output["description"]["en"] == "A nicer mug"
    assert product.output["category_id"] == category_id


@pytest.mark.asyncio
async def test_bulk_import_malicious_image_url_is_a_row_error_not_silent_success(db_session):
    result = await execute_tool(
        "bulk_import_products",
        {
            "rows": [{
                "sku": "SKU-A1-1",
                "base_price": 10,
                "stock_quantity": 10,
                "image_url": "javascript:alert(1)",
            }]
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.output["updated_count"] == 0
    assert result.output["failed_count"] == 1
    product = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert product.output["images"] == []


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


# ---------------------------------------------------------------------------
# Storefront templates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_storefront_templates_tool_returns_all_three(db_session):
    result = await execute_tool("list_storefront_templates", {}, "tenant-a", db_session)
    assert result.is_error is False
    keys = {t["key"] for t in result.output}
    assert keys == {"aurora", "atelier", "nova"}


@pytest.mark.asyncio
async def test_apply_storefront_template_only_stages_until_confirmed(async_client: AsyncClient, db_session):
    # Calling the tool alone must NOT touch any pages — it only stages the switch.
    result = await execute_tool("apply_storefront_template", {"template_key": "aurora"}, "tenant-a", db_session)
    assert result.is_error is False
    assert result.pending_confirmation is not None

    unpublished_home = await async_client.get("/api/v1/store/tenant-a/pages/about")
    assert unpublished_home.status_code == 404  # tenant-a's seed data never published an "about" page

    await ai_pending_action_service.confirm_pending_action_service(
        "tenant-a", result.pending_confirmation.id, db_session
    )

    # Confirming actually seeds AND publishes home/about/contact immediately.
    home_resp = await async_client.get("/api/v1/store/tenant-a/pages/home")
    about_resp = await async_client.get("/api/v1/store/tenant-a/pages/about")
    contact_resp = await async_client.get("/api/v1/store/tenant-a/pages/contact")
    assert home_resp.status_code == 200
    assert about_resp.status_code == 200
    assert contact_resp.status_code == 200
    home_types = [s["type"] for s in home_resp.json()["sections"]]
    assert "hero_banner" in home_types
    assert "product_grid" in home_types

    # Confirming also stamps which template this tenant is now on.
    settings = (await db_session.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == 1)
    )).scalar_one_or_none()
    assert settings is not None
    assert settings.template_key == "aurora"


@pytest.mark.asyncio
async def test_apply_storefront_template_rejects_unknown_key(db_session):
    result = await execute_tool("apply_storefront_template", {"template_key": "not-a-real-template"}, "tenant-a", db_session)
    assert result.is_error is True


@pytest.mark.asyncio
async def test_apply_storefront_template_is_tenant_scoped_on_confirm(async_client: AsyncClient, db_session):
    result = await execute_tool("apply_storefront_template", {"template_key": "nova"}, "tenant-a", db_session)
    confirmation_id = result.pending_confirmation.id

    with pytest.raises(Exception):
        await ai_pending_action_service.confirm_pending_action_service("tenant-b", confirmation_id, db_session)

    # tenant-b never got a nova storefront out of tenant-a's staged action.
    tenant_b_home = await async_client.get("/api/v1/store/tenant-b/pages/home")
    assert tenant_b_home.status_code == 404


@pytest.mark.asyncio
async def test_every_storefront_template_page_is_schema_valid():
    # Catches a malformed section (bad type, missing required settings, over-deep nesting)
    # in the static template data itself, independent of the sanitizer/apply flow.
    assert {t["key"] for t in STOREFRONT_TEMPLATES} == {"aurora", "atelier", "nova"}
    for template in STOREFRONT_TEMPLATES:
        for page_key, page_content in template["pages"].items():
            sections = [Section(**s) for s in page_content["sections"]]
            assert len(sections) > 0, f"{template['key']}/{page_key} has no sections"


# ---------------------------------------------------------------------------
# Router-level: direct (non-AI) template list/apply endpoints — what the admin
# "Templates" picker page actually calls, distinct from the AI-gated tool path above.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_templates_router_endpoint_lists_all_three(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/ai/templates", headers=headers)
    assert response.status_code == 200
    keys = {t["key"] for t in response.json()}
    assert keys == {"aurora", "atelier", "nova"}


@pytest.mark.asyncio
async def test_get_templates_router_endpoint_requires_tenant_admin(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/ai/templates", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_apply_templates_router_endpoint_executes_immediately_and_is_tenant_scoped(
    async_client: AsyncClient, seed_tokens
):
    # Unlike the AI tool path, the direct admin-UI endpoint is the confirmation
    # (the frontend's own ConfirmContext dialog) — no pending-action staging.
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}

    cross_tenant = await async_client.post(
        "/api/v1/admin/store/tenant-b/ai/templates/nova/apply", headers=headers_a
    )
    assert cross_tenant.status_code == 403

    response = await async_client.post("/api/v1/admin/store/tenant-a/ai/templates/nova/apply", headers=headers_a)
    assert response.status_code == 200
    body = response.json()
    assert body["template_key"] == "nova"
    assert {p["page_key"] for p in body["pages"]} == {"home", "about", "contact"}
    assert all(p["has_unpublished_changes"] is False for p in body["pages"])  # published immediately

    live_home = await async_client.get("/api/v1/store/tenant-a/pages/home")
    assert live_home.status_code == 200

    # tenant-b's own storefront is untouched by tenant-a applying a template.
    tenant_b_home = await async_client.get("/api/v1/store/tenant-b/pages/home")
    assert tenant_b_home.status_code == 404


@pytest.mark.asyncio
async def test_apply_templates_router_endpoint_rejects_unknown_key(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/templates/not-a-real-template/apply", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_category_update_and_gated_delete(db_session):
    created = await execute_tool(
        "create_category",
        {"name": {"en": "Hats", "he": "כובעים"}, "slug": "hats"},
        "tenant-a",
        db_session,
    )
    assert created.is_error is False
    category_id = created.output["id"]

    updated = await execute_tool(
        "update_category",
        {"category_id": category_id, "slug": "hats-updated"},
        "tenant-a",
        db_session,
    )
    assert updated.is_error is False
    assert updated.output["slug"] == "hats-updated"

    staged = await execute_tool("delete_category", {"category_id": category_id}, "tenant-a", db_session)
    assert staged.pending_confirmation is not None
    listed = await execute_tool("list_categories", {}, "tenant-a", db_session)
    assert any(c["id"] == category_id for c in listed.output)

    await ai_pending_action_service.confirm_pending_action_service(
        "tenant-a", staged.pending_confirmation.id, db_session
    )
    listed_after = await execute_tool("list_categories", {}, "tenant-a", db_session)
    assert all(c["id"] != category_id for c in listed_after.output)


@pytest.mark.asyncio
async def test_update_and_gated_delete_coupon(db_session):
    listed = await execute_tool("list_coupons", {}, "tenant-a", db_session)
    coupon_id = listed.output[0]["id"]
    updated = await execute_tool(
        "update_coupon",
        {"coupon_id": coupon_id, "discount_val": 25, "min_order_amt": 50},
        "tenant-a",
        db_session,
    )
    assert updated.is_error is False
    assert float(updated.output["discount_val"]) == 25
    assert float(updated.output["min_order_amt"]) == 50

    staged = await execute_tool("delete_coupon", {"coupon_id": coupon_id}, "tenant-a", db_session)
    assert staged.pending_confirmation is not None
    await ai_pending_action_service.cancel_pending_action_service(
        "tenant-a", staged.pending_confirmation.id, db_session
    )
    still = await execute_tool("list_coupons", {}, "tenant-a", db_session)
    assert any(c["id"] == coupon_id for c in still.output)


@pytest.mark.asyncio
async def test_list_reviews_and_set_review_status(db_session):
    listed = await execute_tool("list_reviews", {}, "tenant-a", db_session)
    assert listed.is_error is False
    assert listed.output[0]["id"] == 1
    assert listed.output[0]["is_approved"] is False

    updated = await execute_tool(
        "set_review_status", {"review_id": 1, "status": "approved"}, "tenant-a", db_session
    )
    assert updated.is_error is False
    assert updated.output["is_approved"] is True


@pytest.mark.asyncio
async def test_list_customers_and_store_settings_and_csv_summary(db_session):
    customers = await execute_tool("list_customers", {"query": "customer"}, "tenant-a", db_session)
    assert customers.is_error is False
    assert any("customer@" in c["email"] for c in customers.output)

    settings = await execute_tool("get_store_settings", {}, "tenant-a", db_session)
    assert settings.is_error is False
    assert "stripe_connect" in settings.output
    assert "is_connected" in settings.output["stripe_connect"]

    branded = await execute_tool(
        "update_store_settings",
        {"currency": "USD", "logo_url": "https://images.example.com/logo.png", "primary_color": "#112233"},
        "tenant-a",
        db_session,
    )
    assert branded.is_error is False
    assert branded.output["currency"] == "USD"
    assert branded.output["logo_url"] == "https://images.example.com/logo.png"
    assert branded.output["primary_color"] == "#112233"

    export = await execute_tool("export_orders_csv", {}, "tenant-a", db_session)
    assert export.is_error is False
    assert export.output["report_type"] == "orders"
    assert export.output["row_count"] >= 1
    assert "cannot attach" in export.output["message"].lower()
    assert "reports" in export.output["message"].lower()
    assert "csv is ready" not in export.output["message"].lower()


@pytest.mark.asyncio
async def test_publish_page_is_gated_and_does_not_auto_publish(db_session):
    await execute_tool(
        "update_page_sections",
        {
            "page_key": "home",
            "page_type": "static_page",
            "sections": [{"type": "text_block", "settings": {"heading": {"en": "Hi", "he": "שלום"}, "body": {"en": "x", "he": "x"}}}],
        },
        "tenant-a",
        db_session,
    )
    targets = await execute_tool("list_page_targets", {}, "tenant-a", db_session)
    assert any(t["page_key"] == "home" for t in targets.output)

    staged = await execute_tool(
        "publish_page", {"page_key": "home", "page_type": "static_page"}, "tenant-a", db_session
    )
    # Without grounding context, publish is allowed (opt-in grounding) but still gated.
    assert staged.pending_confirmation is not None
    assert staged.output["status"] == "confirmation_required"


@pytest.mark.asyncio
async def test_update_variant_changes_sku_price_and_stock(db_session):
    result = await execute_tool(
        "update_variant",
        {"variant_id": 1, "sku": "SKU-A1-NEW", "price_override": 19.5, "stock_quantity": 3, "attributes_json": {"size": "L"}},
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.output["sku"] == "SKU-A1-NEW"
    assert result.output["stock_quantity"] == 3
    assert result.output["attributes_json"]["size"] == "L"
    assert float(result.output["price_override"]) == 19.5


@pytest.mark.asyncio
async def test_fulfill_order_only_stages_until_confirmed(db_session):
    from fastapi import HTTPException

    processing = await execute_tool(
        "update_order_status", {"order_id": 1, "status": "processing"}, "tenant-a", db_session
    )
    assert processing.is_error is False

    staged = await execute_tool(
        "fulfill_order", {"order_id": 1, "provider_override": "hfd"}, "tenant-a", db_session
    )
    assert staged.is_error is False
    assert staged.pending_confirmation is not None
    assert staged.output["status"] == "confirmation_required"

    details = await execute_tool("get_order_details", {"order_id": 1}, "tenant-a", db_session)
    assert details.output["status"] == "processing"

    with pytest.raises(HTTPException) as exc:
        await ai_pending_action_service.confirm_pending_action_service(
            "tenant-a", staged.pending_confirmation.id, db_session
        )
    assert exc.value.status_code == 422

    still_processing = await execute_tool("get_order_details", {"order_id": 1}, "tenant-a", db_session)
    assert still_processing.output["status"] == "processing"


@pytest.mark.asyncio
async def test_category_parent_id_rejects_self_cross_tenant_and_cycles(db_session):
    parent = await execute_tool(
        "create_category",
        {"name": {"en": "Parent", "he": "הורה"}, "slug": "parent-ai"},
        "tenant-a",
        db_session,
    )
    assert parent.is_error is False
    parent_id = parent.output["id"]

    child = await execute_tool(
        "create_category",
        {"name": {"en": "Child", "he": "ילד"}, "slug": "child-ai", "parent_id": parent_id},
        "tenant-a",
        db_session,
    )
    assert child.is_error is False
    child_id = child.output["id"]

    self_parent = await execute_tool(
        "update_category", {"category_id": parent_id, "parent_id": parent_id}, "tenant-a", db_session
    )
    assert self_parent.is_error is True
    assert "own parent" in str(self_parent.output).lower()

    cycle = await execute_tool(
        "update_category", {"category_id": parent_id, "parent_id": child_id}, "tenant-a", db_session
    )
    assert cycle.is_error is True
    assert "cycle" in str(cycle.output).lower()

    other = await execute_tool(
        "create_category",
        {"name": {"en": "Other", "he": "אחר"}, "slug": "other-ai"},
        "tenant-b",
        db_session,
    )
    assert other.is_error is False
    cross = await execute_tool(
        "update_category",
        {"category_id": parent_id, "parent_id": other.output["id"]},
        "tenant-a",
        db_session,
    )
    assert cross.is_error is True
    assert "parent" in str(cross.output).lower()
