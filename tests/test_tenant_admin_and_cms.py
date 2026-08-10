import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.tenant import Tenant, SubscriptionPlan

@pytest.mark.asyncio
async def test_create_product_within_subscription_limit(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {
        "name": {"en": "New Product", "he": "מוצר חדש"},
        "slug": "new-product",
        "base_price": "100.00",
        "is_active": True,
        "variants": [],
        "images": []
    }
    response = await async_client.post("/api/v1/admin/store/tenant-a/products", json=payload, headers=headers)
    assert response.status_code == 201

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_payload", [
    {"name": {"en": "A"}, "slug": "slug", "base_price": "100", "is_active": True, "variants": [], "images": []}, # Name too short
    {"name": "Valid", "slug": "slug", "base_price": "-10.00", "is_active": True, "variants": [], "images": []}, # Negative price
    {"name": "Valid", "slug": "slug", "base_price": "0", "is_active": True, "variants": [], "images": []}, # Zero price
])
async def test_create_product_validation_failures(async_client: AsyncClient, seed_tokens, invalid_payload):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.post("/api/v1/admin/store/tenant-a/products", json=invalid_payload, headers=headers)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_create_product_exceeding_subscription_limit(async_client: AsyncClient, seed_tokens, db_session):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}

    # tenant-a is seeded with 1 product already. Cap its plan at 1 product so the
    # next creation attempt is guaranteed to exceed the limit.
    tenant_result = await db_session.execute(select(Tenant).where(Tenant.slug == "tenant-a"))
    tenant = tenant_result.scalar_one()
    plan_result = await db_session.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan_id))
    plan = plan_result.scalar_one()
    plan.max_products = 1
    await db_session.commit()

    payload = {
        "name": {"en": "Limit Product", "he": "מוצר גבול"},
        "slug": "limit-product",
        "base_price": "100.00",
        "is_active": True,
        "variants": [{"sku": "LIMIT-1", "stock_quantity": 5}],
        "images": []
    }
    response = await async_client.post("/api/v1/admin/store/tenant-a/products", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Maximum number of products" in response.text

@pytest.mark.asyncio
async def test_get_update_delete_product_lifecycle(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    create_payload = {
        "name": {"en": "Editable Product", "he": "מוצר לעריכה"},
        "slug": "editable-product",
        "base_price": "50.00",
        "is_active": True,
        "variants": [{"sku": "EDIT-1", "stock_quantity": 5}],
        "images": []
    }
    create_resp = await async_client.post("/api/v1/admin/store/tenant-a/products", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]

    # GET returns the product, prefill-ready
    get_resp = await async_client.get(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"]["en"] == "Editable Product"

    # PUT actually persists the change — this used to be a stub that ignored the request
    update_resp = await async_client.put(
        f"/api/v1/admin/store/tenant-a/products/{product_id}",
        json={"name": {"en": "Renamed Product", "he": "מוצר לעריכה"}, "base_price": "75.00"},
        headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"]["en"] == "Renamed Product"
    assert float(update_resp.json()["base_price"]) == 75.00

    reget_resp = await async_client.get(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers)
    assert reget_resp.json()["name"]["en"] == "Renamed Product"

    # DELETE actually removes the row — this used to be a no-op stub
    delete_resp = await async_client.delete(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers)
    assert delete_resp.status_code == 204

    postdelete_resp = await async_client.get(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers)
    assert postdelete_resp.status_code == 404

@pytest.mark.asyncio
async def test_product_get_update_delete_are_tenant_isolated(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}
    create_payload = {
        "name": {"en": "Tenant A Only", "he": "רק לדייר א"},
        "slug": "tenant-a-only",
        "base_price": "30.00",
        "is_active": True,
        "variants": [],
        "images": []
    }
    create_resp = await async_client.post("/api/v1/admin/store/tenant-a/products", json=create_payload, headers=headers_a)
    product_id = create_resp.json()["id"]

    # tenant-b's admin acting against tenant-a's product route must not see or affect it
    get_resp = await async_client.get(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers_b)
    assert get_resp.status_code == 403

    update_resp = await async_client.put(
        f"/api/v1/admin/store/tenant-a/products/{product_id}",
        json={"name": {"en": "Hijacked", "he": "נחטף"}},
        headers=headers_b
    )
    assert update_resp.status_code == 403

    delete_resp = await async_client.delete(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers_b)
    assert delete_resp.status_code == 403

    still_there = await async_client.get(f"/api/v1/admin/store/tenant-a/products/{product_id}", headers=headers_a)
    assert still_there.status_code == 200
    assert still_there.json()["name"]["en"] == "Tenant A Only"

@pytest.mark.asyncio
async def test_update_order_status(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.patch("/api/v1/admin/store/tenant-a/orders/1/status?status=processing", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_update_order_invalid_status_transition(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    # Invalid enum status string should result in 422
    response = await async_client.patch("/api/v1/admin/store/tenant-a/orders/1/status?status=invalid_status", headers=headers)
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_update_store_settings(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {
        "primary_color": "#FF0000",
        "currency": "USD"
    }
    response = await async_client.put("/api/v1/admin/store/tenant-a/settings", json=payload, headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_export_orders_csv(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/reports/export?report_type=orders", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_product_review_moderation(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.patch("/api/v1/admin/store/tenant-a/reviews/1/status?status=approved", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_add_product_variant(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {
        "sku": "SKU-A1-2",
        "attributes_json": {"color": "blue", "size": "L"},
        "price_override": "12.50",
        "stock_quantity": 25
    }
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/products/1/variants", json=payload, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sku"] == "SKU-A1-2"
    assert body["stock_quantity"] == 25
    assert float(body["price_override"]) == 12.50
    assert body["id"] is not None

    # The new variant shows up when the product is re-fetched.
    get_resp = await async_client.get("/api/v1/admin/store/tenant-a/products/1", headers=headers)
    skus = [v["sku"] for v in get_resp.json()["variants"]]
    assert "SKU-A1-2" in skus

@pytest.mark.asyncio
async def test_add_product_variant_product_not_found(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {"sku": "SKU-X", "stock_quantity": 1}
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/products/999999/variants", json=payload, headers=headers
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_add_product_variant_is_tenant_isolated(async_client: AsyncClient, seed_tokens):
    # Product 1 belongs to tenant-a; tenant-b's admin must not be able to add a variant to it.
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}
    payload = {"sku": "HIJACK-SKU", "stock_quantity": 1}
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/products/1/variants", json=payload, headers=headers_b
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_product_variant_persists_stock_and_price(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {
        "sku": "SKU-A1-1",
        "attributes_json": {"color": "red"},
        "price_override": "15.00",
        "stock_quantity": 42
    }
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/variants/1", json=payload, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stock_quantity"] == 42
    assert float(body["price_override"]) == 15.00
    assert body["attributes_json"] == {"color": "red"}

    get_resp = await async_client.get("/api/v1/admin/store/tenant-a/products/1", headers=headers)
    updated_variant = next(v for v in get_resp.json()["variants"] if v["id"] == 1)
    assert updated_variant["stock_quantity"] == 42

@pytest.mark.asyncio
async def test_update_product_variant_not_found(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {"sku": "SKU-X", "stock_quantity": 1}
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/variants/999999", json=payload, headers=headers
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_product_variant_is_tenant_isolated(async_client: AsyncClient, seed_tokens):
    # Variant 1 belongs to tenant-a; tenant-b's admin must not be able to modify it.
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}
    payload = {"sku": "HIJACK-SKU", "stock_quantity": 999}
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/variants/1", json=payload, headers=headers_b
    )
    assert response.status_code == 403

    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    get_resp = await async_client.get("/api/v1/admin/store/tenant-a/products/1", headers=headers_a)
    variant = next(v for v in get_resp.json()["variants"] if v["id"] == 1)
    assert variant["sku"] != "HIJACK-SKU"

@pytest.mark.asyncio
async def test_list_tenant_orders_includes_customer_identity(async_client: AsyncClient, seed_tokens):
    # Order 1 is seeded for user_id=4 ("Customer A", customer@tenanta.com). The
    # admin orders list used to return the bare Order row (no customer_name/
    # customer_email field exists on it), so the frontend always showed "Guest".
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/orders", headers=headers)
    assert response.status_code == 200
    body = response.json()
    orders = body["data"] if isinstance(body, dict) else body
    order = next(o for o in orders if o["id"] == 1)
    assert order["customer_name"] == "Customer A"
    assert order["customer_email"] == "customer@tenanta.com"

@pytest.mark.asyncio
async def test_get_tenant_order_includes_customer_identity(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/orders/1", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["customer_name"] == "Customer A"
    assert body["customer_email"] == "customer@tenanta.com"
    assert body["items"] == [] or isinstance(body["items"], list)

@pytest.mark.asyncio
async def test_tenant_orders_are_tenant_isolated(async_client: AsyncClient, seed_tokens):
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/orders", headers=headers_b)
    assert response.status_code == 403

    response = await async_client.get("/api/v1/admin/store/tenant-a/orders/1", headers=headers_b)
    assert response.status_code in (403, 404)
