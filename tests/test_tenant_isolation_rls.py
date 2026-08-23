import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_user_cannot_view_another_users_order(async_client: AsyncClient, seed_tokens):
    # Ownership isolation, not store isolation: order 1 (seeded) belongs to
    # the global customer (user id 4). tenant_admin_a is a *different* global
    # user (id 2) with no orders of their own -- under global identity this
    # is what "can't see someone else's order" actually tests, since a store
    # boundary no longer implies a different account.
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/customer/orders/1", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_tenant_admin_a_cannot_access_tenant_b_admin_routes(async_client: AsyncClient, seed_tokens):
    # Still a real security boundary: tenant_admin membership is never
    # auto-provisioned (see deps.get_tenant_admin), so holding a valid global
    # login is not enough to administer a store you were never granted.
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-b/orders", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_global_customer_can_legitimately_use_either_store(async_client: AsyncClient, seed_tokens):
    # This replaces the old "cross-tenant JWT injection attack" test: under
    # global identity, a customer using the *same* account at a second store
    # is the intended behavior, not an attack. seed_tokens["customer_a"] (see
    # conftest.py) is a global user with an active 'customer' membership at
    # both tenant-a and tenant-b, so neither request should ever be rejected
    # for lack of store authorization (403) -- an empty/unknown cart is a
    # legitimate 400, which is what proves get_tenant_customer let them in.
    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {
        "cart_id": "00000000-0000-0000-0000-000000000000",
        "shipping_address": {},
        "payment_token": "11111111-1111-1111-1111-111111111111"
    }
    response_a = await async_client.post("/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response_a.status_code != 403

    response_b = await async_client.post("/api/v1/store/tenant-b/cart/checkout", json=payload, headers=headers)
    assert response_b.status_code != 403

@pytest.mark.asyncio
async def test_customer_auto_joins_new_store_on_first_visit(async_client: AsyncClient, seed_tokens, db_session):
    # A brand-new global user (no memberships at all yet) should still be let
    # in as a customer the first time they touch any active store -- that's
    # the mechanism that makes "one login, every store" work without a
    # separate per-store registration step.
    from sqlalchemy import select
    from app.core.security import create_access_token, get_password_hash
    from app.models.user import User

    fresh_user = User(email="brandnew@example.com", password_hash=get_password_hash("password"), full_name="Brand New", role="user")
    db_session.add(fresh_user)
    await db_session.commit()
    await db_session.refresh(fresh_user)

    token = f"Bearer {create_access_token(str(fresh_user.id))}"
    response = await async_client.post(
        "/api/v1/store/tenant-a/reviews",
        json={"product_id": 1, "rating": 5, "comment": "First time here"},
        headers={"Authorization": token},
    )
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_public_catalog_only_returns_current_tenant_products(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products")
    assert response.status_code == 200
    data = response.json()
    for product in data.get("data", []):
        assert product["tenant_id"] == 1 # tenant-a is ID 1

@pytest.mark.asyncio
async def test_idor_product_variant_manipulation(async_client: AsyncClient):
    payload = {
        "variant_id": 9999, # Belonging to tenant-b
        "quantity": 1
    }
    # Adding tenant B's variant to tenant A's cart
    response = await async_client.post("/api/v1/store/tenant-a/cart/00000000-0000-0000-0000-000000000000/items", json=payload)
    assert response.status_code in (404, 422)

@pytest.mark.asyncio
async def test_cannot_add_store_a_product_to_store_b_cart(async_client: AsyncClient):
    cart_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    add_b = await async_client.post(
        f"/api/v1/store/tenant-b/cart/{cart_id}/items",
        json={"variant_id": 2, "quantity": 1},
    )
    assert add_b.status_code == 201

    cross = await async_client.post(
        f"/api/v1/store/tenant-b/cart/{cart_id}/items",
        json={"variant_id": 1, "quantity": 1},
    )
    assert cross.status_code == 404

@pytest.mark.asyncio
async def test_cannot_reuse_store_a_cart_on_store_b_routes(async_client: AsyncClient):
    cart_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    created = await async_client.post(
        f"/api/v1/store/tenant-a/cart/{cart_id}/items",
        json={"variant_id": 1, "quantity": 1},
    )
    assert created.status_code == 201

    fetched = await async_client.get(f"/api/v1/store/tenant-b/cart/{cart_id}")
    assert fetched.status_code == 404

    added = await async_client.post(
        f"/api/v1/store/tenant-b/cart/{cart_id}/items",
        json={"variant_id": 2, "quantity": 1},
    )
    assert added.status_code == 404

@pytest.mark.asyncio
async def test_disabled_user_token_is_rejected_on_optional_cart_routes(async_client: AsyncClient, db_session, seed_tokens):
    from sqlalchemy import update
    from app.models.user import User

    await db_session.execute(update(User).where(User.id == 4).values(is_active=False))
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/store/tenant-a/cart/cccccccc-cccc-cccc-cccc-cccccccccccc/items",
        json={"variant_id": 1, "quantity": 1},
        headers={"Authorization": seed_tokens["customer_a"]},
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_guest_cart_requires_capability_token_after_creation(async_client: AsyncClient):
    # Cart.id is a client-generated UUID with no secrecy of its own.
    # Creating a cart is fine with just the id (nobody to impersonate yet),
    # but *reading it back* must require the capability token minted at
    # creation -- the bare UUID alone must never be enough.
    cart_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    created = await async_client.post(
        f"/api/v1/store/tenant-a/cart/{cart_id}/items",
        json={"variant_id": 1, "quantity": 1},
    )
    assert created.status_code == 201
    token = created.json()["cart_token"]
    assert token

    no_token = await async_client.get(f"/api/v1/store/tenant-a/cart/{cart_id}")
    assert no_token.status_code == 404

    wrong_token = await async_client.get(
        f"/api/v1/store/tenant-a/cart/{cart_id}",
        # Well-formed (unexpired exp + hex signature) but not one the server
        # ever issued -- must fail the HMAC comparison, not just parsing.
        headers={"X-Cart-Token": "9999999999." + "0" * 64},
    )
    assert wrong_token.status_code == 404

    with_token = await async_client.get(
        f"/api/v1/store/tenant-a/cart/{cart_id}",
        headers={"X-Cart-Token": token},
    )
    assert with_token.status_code == 200
    assert with_token.json()["items"][0]["variant_id"] == 1

@pytest.mark.asyncio
async def test_guest_cart_is_claimed_on_login_and_then_ignores_the_token(async_client: AsyncClient, seed_tokens):
    cart_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    created = await async_client.post(
        f"/api/v1/store/tenant-a/cart/{cart_id}/items",
        json={"variant_id": 1, "quantity": 1},
    )
    token = created.json()["cart_token"]

    # Touching the cart while authenticated (with the capability token still
    # required, since it's not claimed yet) is what claims it for the user.
    claim = await async_client.get(
        f"/api/v1/store/tenant-a/cart/{cart_id}",
        headers={"Authorization": seed_tokens["customer_a"], "X-Cart-Token": token},
    )
    assert claim.status_code == 200

    # Now claimed: the owning user's session alone is enough, no token needed.
    still_owned = await async_client.get(
        f"/api/v1/store/tenant-a/cart/{cart_id}",
        headers={"Authorization": seed_tokens["customer_a"]},
    )
    assert still_owned.status_code == 200

    # But it's a different global user's own auth now, so the old capability
    # token can't be replayed by anyone else to get back in.
    other_user = await async_client.get(
        f"/api/v1/store/tenant-a/cart/{cart_id}",
        headers={"Authorization": seed_tokens["tenant_admin_a"], "X-Cart-Token": token},
    )
    assert other_user.status_code == 404

@pytest.mark.asyncio
async def test_customer_orders_can_be_filtered_by_tenant_slug(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    all_orders = await async_client.get("/api/v1/customer/orders", headers=headers)
    assert all_orders.status_code == 200
    assert any(order["tenant_id"] == 1 for order in all_orders.json()["data"])
    assert all_orders.json()["data"][0]["tenant_slug"] == "tenant-a"

    store_b = await async_client.get("/api/v1/customer/orders?tenant_slug=tenant-b", headers=headers)
    assert store_b.status_code == 200
    assert store_b.json()["data"] == []

@pytest.mark.asyncio
async def test_customer_order_detail_rejects_wrong_store_context(async_client: AsyncClient, seed_tokens):
    # Order 1 (seeded) belongs to the global customer (user id 4) at
    # tenant-a. Owning it is not enough once a caller narrows to a specific
    # store's context: user_id ownership alone must not let it leak across
    # a store boundary the caller explicitly asked to stay within.
    headers = {"Authorization": seed_tokens["customer_a"]}

    same_store = await async_client.get("/api/v1/customer/orders/1?tenant_slug=tenant-a", headers=headers)
    assert same_store.status_code == 200

    wrong_store = await async_client.get("/api/v1/customer/orders/1?tenant_slug=tenant-b", headers=headers)
    assert wrong_store.status_code == 404

    global_view = await async_client.get("/api/v1/customer/orders/1", headers=headers)
    assert global_view.status_code == 200
