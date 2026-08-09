import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_customer_a_cannot_view_tenant_b_orders(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    response = await async_client.get("/api/v1/customer/orders/123", headers=headers) # Assuming 123 is tenant B order
    # Depending on implementation, it might be 404 if not found in tenant scope, or 403 if it explicitly blocks cross-tenant
    assert response.status_code in (404, 403)

@pytest.mark.asyncio
async def test_tenant_admin_a_cannot_access_tenant_b_admin_routes(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-b/orders", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_cross_tenant_jwt_injection_attack(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]} # customer A is for tenant-a
    payload = {
        "cart_id": "00000000-0000-0000-0000-000000000000",
        "shipping_address": {},
        "payment_token": "11111111-1111-1111-1111-111111111111"
    }
    # customer_a tries to checkout in tenant-b store
    response = await async_client.post("/api/v1/store/tenant-b/cart/checkout", json=payload, headers=headers)
    assert response.status_code == 403

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
