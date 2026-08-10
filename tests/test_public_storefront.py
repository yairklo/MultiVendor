import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_store_config(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/config")
    assert response.status_code == 200
    data = response.json()
    assert "primary_color" in data
    assert "currency" in data

@pytest.mark.asyncio
async def test_get_store_config_invalid_tenant(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/invalid-tenant/config")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_store_config_with_null_supported_languages(async_client: AsyncClient, db_session):
    # A settings row created before supported_languages was ever set (or via
    # a path that leaves it NULL) used to 500 the whole config endpoint,
    # since the response schema required a list.
    from app.models.tenant import TenantSettings

    db_session.add(TenantSettings(tenant_id=1, primary_color="#123456", currency="USD"))
    await db_session.commit()

    response = await async_client.get("/api/v1/store/tenant-a/config")
    assert response.status_code == 200
    data = response.json()
    assert data["supported_languages"] == ["he"]
    assert data["primary_color"] == "#123456"

@pytest.mark.asyncio
async def test_list_products_with_pagination_and_search(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products?page=1&page_size=10&q=test&category_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "meta" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 10
    assert "data" in data

@pytest.mark.asyncio
@pytest.mark.parametrize("page, page_size, expected_status", [
    (0, 10, 422), # page ge=1
    (-1, 10, 422), 
    (1, 0, 422),  # page_size ge=1
    (1, 500, 422) # page_size le=100
])
async def test_list_products_pagination_boundaries(async_client: AsyncClient, page, page_size, expected_status):
    response = await async_client.get(f"/api/v1/store/tenant-a/products?page={page}&page_size={page_size}")
    assert response.status_code == expected_status

@pytest.mark.asyncio
async def test_inactive_products_hidden_from_public(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products")
    assert response.status_code == 200
    data = response.json()
    for product in data.get("data", []):
        assert product["is_active"] is True

@pytest.mark.asyncio
async def test_get_product_details_with_variants_and_images(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products/product-a1")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "product-a1"
    assert "variants" in data
    assert "images" in data
