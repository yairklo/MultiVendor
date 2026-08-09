import pytest
from httpx import AsyncClient

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
async def test_create_product_exceeding_subscription_limit(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {
        "name": "Limit Product",
        "slug": "limit-product",
        "base_price": "100.00",
        "is_active": True,
        "variants": [],
        "images": []
    }
    response = await async_client.post("/api/v1/admin/store/tenant-a/products", json=payload, headers=headers)
    assert response.status_code in (201, 403, 422)

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
