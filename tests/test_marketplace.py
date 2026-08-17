import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_global_customer_login_works_across_store_scopes(async_client: AsyncClient, seed_tokens):
    # One login (see test_auth_and_onboarding.py::test_login_without_tenant_slug_still_succeeds
    # for that part), and the resulting token is valid at every store the
    # account has a membership at -- the core promise of global identity.
    # seed_tokens builds tokens directly (no HTTP call), deliberately not
    # going through /auth/login here: that endpoint is rate-limited and other
    # tests in the suite exercise it heavily, so a real login call in this
    # test would be flaky depending on run order.
    headers = {"Authorization": seed_tokens["customer_a"]}

    me = await async_client.get("/api/v1/customer/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "customer@gmail.com"

    for tenant_slug in ("tenant-a", "tenant-b"):
        resp = await async_client.get(f"/api/v1/store/{tenant_slug}/config", headers=headers)
        assert resp.status_code == 200

@pytest.mark.asyncio
async def test_marketplace_product_visibility_rules(async_client: AsyncClient):
    # tenant-a has show_all_products_in_marketplace=TRUE (seeded), so its
    # product 1 is visible even without its own flag set. tenant-b has it
    # FALSE, so only product 2 (show_in_marketplace=TRUE) appears -- product 3
    # (show_in_marketplace=FALSE, seeded specifically as the negative case)
    # must not.
    response = await async_client.get("/api/v1/marketplace/products", params={"page_size": 50})
    assert response.status_code == 200
    slugs = {p["slug"] for p in response.json()["data"]}
    assert "product-a1" in slugs
    assert "product-b1" in slugs
    assert "product-b2" not in slugs

@pytest.mark.asyncio
async def test_marketplace_checkout_splits_order_per_vendor(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())

    # variant 1 -> product-a1 (tenant-a, unit price 10.00), variant 2 -> product-b1 (tenant-b, unit price 20.00)
    add_a = await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 2}, headers=headers)
    assert add_a.status_code == 201
    add_b = await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 2, "quantity": 1}, headers=headers)
    assert add_b.status_code == 201

    cart = await async_client.get(f"/api/v1/marketplace/cart/{cart_id}")
    assert cart.status_code == 200
    cart_data = cart.json()
    assert cart_data["vendor_count"] == 2
    assert float(cart_data["subtotal"]) == 40.00  # 2*10.00 + 1*20.00

    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={
            "cart_id": cart_id,
            "shipping_address": {"city": "Tel Aviv"},
            "payment_token": str(uuid.uuid4()),
        },
        headers=headers,
    )
    assert checkout.status_code == 201
    data = checkout.json()
    assert float(data["total_amount"]) == 40.00
    assert len(data["sub_orders"]) == 2

    by_tenant = {so["tenant_id"]: so for so in data["sub_orders"]}
    assert float(by_tenant[1]["subtotal"]) == 20.00  # 2 * 10.00
    assert float(by_tenant[2]["subtotal"]) == 20.00  # 1 * 20.00
    # Every sub-order is its own real Order row: pending_payment, its own
    # order_number, no cross-vendor bleed in the totals.
    for so in data["sub_orders"]:
        assert so["status"] == "pending_payment"
        assert so["order_number"].startswith("ORD-")

    # Cart is now empty -- checkout consumed it.
    empty_cart = await async_client.get(f"/api/v1/marketplace/cart/{cart_id}")
    assert empty_cart.json()["items"] == []

@pytest.mark.asyncio
async def test_marketplace_checkout_computes_commission_and_payout(async_client: AsyncClient, seed_tokens, db_session):
    from decimal import Decimal
    from sqlalchemy import select
    from app.models.order import Order

    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())

    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1}, headers=headers)

    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={"cart_id": cart_id, "shipping_address": {"city": "Tel Aviv"}, "payment_token": str(uuid.uuid4())},
        headers=headers,
    )
    assert checkout.status_code == 201
    sub_order = checkout.json()["sub_orders"][0]
    assert Decimal(sub_order["subtotal"]) == Decimal("10.00")

    # commission/payout aren't on OrderResponse (deliberately not exposed to
    # the customer-facing checkout response), so verify them straight from
    # the Order row: server/app/services/marketplace_service.py has
    # PLATFORM_COMMISSION_RATE = 0.10 -> commission 1.00, payout 9.00 on a 10.00 subtotal.
    order = (await db_session.execute(select(Order).where(Order.id == sub_order["id"]))).scalar_one()
    assert order.platform_commission == Decimal("1.00")
    assert order.vendor_net_payout == Decimal("9.00")
    assert order.platform_commission + order.vendor_net_payout == order.subtotal

@pytest.mark.asyncio
async def test_marketplace_checkout_fails_on_insufficient_stock(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())

    # variant 3 (product-b2) is seeded with stock_quantity=5.
    add = await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 3, "quantity": 5}, headers=headers)
    assert add.status_code == 201

    # A second request for the same variant tips total requested quantity to
    # 10, which exceeds the 5 in stock once the cart is checked out.
    add_more = await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 3, "quantity": 5}, headers=headers)
    assert add_more.status_code == 201

    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={"cart_id": cart_id, "shipping_address": {"city": "Tel Aviv"}, "payment_token": str(uuid.uuid4())},
        headers=headers,
    )
    assert checkout.status_code == 400

    # Failed checkout must not have consumed the cart or touched stock.
    cart = await async_client.get(f"/api/v1/marketplace/cart/{cart_id}")
    assert len(cart.json()["items"]) == 1
    assert cart.json()["items"][0]["quantity"] == 10

@pytest.mark.asyncio
async def test_marketplace_checkout_requires_shipping_address_for_physical_goods(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1}, headers=headers)

    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={"cart_id": cart_id, "payment_token": str(uuid.uuid4())},  # no shipping_address
        headers=headers,
    )
    assert checkout.status_code == 400

@pytest.mark.asyncio
async def test_marketplace_cart_update_and_remove_item(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    add = await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1}, headers=headers)
    assert add.status_code == 201

    cart = await async_client.get(f"/api/v1/marketplace/cart/{cart_id}")
    item_id = cart.json()["items"][0]["id"]

    update = await async_client.patch(f"/api/v1/marketplace/cart/{cart_id}/items/{item_id}", json={"quantity": 3})
    assert update.status_code == 200
    cart_after_update = await async_client.get(f"/api/v1/marketplace/cart/{cart_id}")
    assert cart_after_update.json()["items"][0]["quantity"] == 3

    remove = await async_client.delete(f"/api/v1/marketplace/cart/{cart_id}/items/{item_id}")
    assert remove.status_code == 200
    cart_after_remove = await async_client.get(f"/api/v1/marketplace/cart/{cart_id}")
    assert cart_after_remove.json()["items"] == []

@pytest.mark.asyncio
async def test_tenant_admin_cannot_view_another_vendors_sub_order(async_client: AsyncClient, seed_tokens):
    customer_headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1}, headers=customer_headers)
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 2, "quantity": 1}, headers=customer_headers)

    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={"cart_id": cart_id, "shipping_address": {"city": "Tel Aviv"}, "payment_token": str(uuid.uuid4())},
        headers=customer_headers,
    )
    assert checkout.status_code == 201
    by_tenant = {so["tenant_id"]: so for so in checkout.json()["sub_orders"]}
    tenant_b_order_id = by_tenant[2]["id"]

    # tenant_admin_a has no membership at tenant-b: fetching tenant-b's
    # sub-order through tenant-b's own admin route must 403, and tenant-a's
    # own order list must never surface a vendor it doesn't own.
    admin_a_headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    cross_vendor = await async_client.get(f"/api/v1/admin/store/tenant-b/orders/{tenant_b_order_id}", headers=admin_a_headers)
    assert cross_vendor.status_code == 403

    admin_a_own_orders = await async_client.get("/api/v1/admin/store/tenant-a/orders", headers=admin_a_headers)
    assert admin_a_own_orders.status_code == 200
    own_order_ids = {o["id"] for o in admin_a_own_orders.json()}
    assert tenant_b_order_id not in own_order_ids

    admin_b_headers = {"Authorization": seed_tokens["tenant_admin_b"]}
    same_vendor = await async_client.get(f"/api/v1/admin/store/tenant-b/orders/{tenant_b_order_id}", headers=admin_b_headers)
    assert same_vendor.status_code == 200
    assert same_vendor.json()["tenant_id"] == 2

@pytest.mark.asyncio
async def test_product_level_marketplace_toggle_changes_listing(async_client: AsyncClient, seed_tokens):
    # product-b2 (id 3) is seeded with show_in_marketplace=FALSE on a tenant
    # that also has show_all_products_in_marketplace=FALSE -- flipping just
    # the product flag must be enough to surface it, and flipping it back
    # must remove it again.
    admin_headers = {"Authorization": seed_tokens["tenant_admin_b"]}

    before = await async_client.get("/api/v1/marketplace/products", params={"page_size": 50})
    assert "product-b2" not in {p["slug"] for p in before.json()["data"]}

    enable = await async_client.put(
        "/api/v1/admin/store/tenant-b/products/3", headers=admin_headers, json={"show_in_marketplace": True}
    )
    assert enable.status_code == 200
    assert enable.json()["show_in_marketplace"] is True

    after_enable = await async_client.get("/api/v1/marketplace/products", params={"page_size": 50})
    assert "product-b2" in {p["slug"] for p in after_enable.json()["data"]}

    disable = await async_client.put(
        "/api/v1/admin/store/tenant-b/products/3", headers=admin_headers, json={"show_in_marketplace": False}
    )
    assert disable.status_code == 200
    after_disable = await async_client.get("/api/v1/marketplace/products", params={"page_size": 50})
    assert "product-b2" not in {p["slug"] for p in after_disable.json()["data"]}

@pytest.mark.asyncio
async def test_store_level_marketplace_toggle_changes_listing(async_client: AsyncClient, seed_tokens):
    # Flipping tenant-b's store-wide flag on must surface ALL its active
    # products (both product-b1, already individually opted in, and
    # product-b2, which is not) without touching either product's own flag.
    admin_headers = {"Authorization": seed_tokens["tenant_admin_b"]}

    enable = await async_client.put(
        "/api/v1/admin/store/tenant-b/marketplace-visibility",
        headers=admin_headers,
        json={"show_all_products_in_marketplace": True},
    )
    assert enable.status_code == 200
    assert enable.json()["show_all_products_in_marketplace"] is True

    listing = await async_client.get("/api/v1/marketplace/products", params={"page_size": 50})
    slugs = {p["slug"] for p in listing.json()["data"]}
    assert "product-b1" in slugs
    assert "product-b2" in slugs

    disable = await async_client.put(
        "/api/v1/admin/store/tenant-b/marketplace-visibility",
        headers=admin_headers,
        json={"show_all_products_in_marketplace": False},
    )
    assert disable.status_code == 200
    listing_after = await async_client.get("/api/v1/marketplace/products", params={"page_size": 50})
    slugs_after = {p["slug"] for p in listing_after.json()["data"]}
    assert "product-b1" in slugs_after  # still individually opted in
    assert "product-b2" not in slugs_after

@pytest.mark.asyncio
async def test_marketplace_visibility_toggle_is_tenant_isolated(async_client: AsyncClient, seed_tokens):
    admin_b_headers = {"Authorization": seed_tokens["tenant_admin_b"]}
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/marketplace-visibility",
        headers=admin_b_headers,
        json={"show_all_products_in_marketplace": True},
    )
    assert response.status_code == 403

async def _checkout_two_vendor_cart(async_client: AsyncClient, headers: dict) -> dict:
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1}, headers=headers)
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 2, "quantity": 1}, headers=headers)
    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={"cart_id": cart_id, "shipping_address": {"city": "Tel Aviv"}, "payment_token": str(uuid.uuid4())},
        headers=headers,
    )
    assert checkout.status_code == 201
    return checkout.json()

@pytest.mark.asyncio
async def test_get_master_order_returns_all_sub_orders(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    master = await _checkout_two_vendor_cart(async_client, headers)

    response = await async_client.get(f"/api/v1/marketplace/orders/{master['id']}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["master_order_number"] == master["master_order_number"]
    assert float(data["total_amount"]) == float(master["total_amount"])
    assert {so["id"] for so in data["sub_orders"]} == {so["id"] for so in master["sub_orders"]}
    assert all(so["status"] == "pending_payment" for so in data["sub_orders"])

@pytest.mark.asyncio
async def test_get_master_order_is_owner_scoped(async_client: AsyncClient, seed_tokens):
    # customer_a and customer_b are the same global user in this seed (see
    # conftest.py), so ownership here is instead verified against a party
    # with no claim at all on the order: a tenant_admin who never checked out.
    headers = {"Authorization": seed_tokens["customer_a"]}
    master = await _checkout_two_vendor_cart(async_client, headers)

    other_headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get(f"/api/v1/marketplace/orders/{master['id']}", headers=other_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_pay_master_order_marks_every_sub_order_processing(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    master = await _checkout_two_vendor_cart(async_client, headers)

    pay = await async_client.post(f"/api/v1/marketplace/orders/{master['id']}/pay", headers=headers)
    assert pay.status_code == 200
    data = pay.json()
    assert len(data["sub_orders"]) == 2
    assert all(so["status"] == "processing" for so in data["sub_orders"])

    # Reflected via the same read path too, not just the pay response.
    fetched = await async_client.get(f"/api/v1/marketplace/orders/{master['id']}", headers=headers)
    assert all(so["status"] == "processing" for so in fetched.json()["sub_orders"])

@pytest.mark.asyncio
async def test_pay_master_order_twice_fails(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    master = await _checkout_two_vendor_cart(async_client, headers)

    first = await async_client.post(f"/api/v1/marketplace/orders/{master['id']}/pay", headers=headers)
    assert first.status_code == 200

    second = await async_client.post(f"/api/v1/marketplace/orders/{master['id']}/pay", headers=headers)
    assert second.status_code == 400

@pytest.mark.asyncio
async def test_pay_master_order_requires_ownership(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    master = await _checkout_two_vendor_cart(async_client, headers)

    other_headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.post(f"/api/v1/marketplace/orders/{master['id']}/pay", headers=other_headers)
    assert response.status_code == 404
