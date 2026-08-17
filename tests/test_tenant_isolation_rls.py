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
