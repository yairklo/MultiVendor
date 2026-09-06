import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.catalog import Product
from app.models.tenant import TenantSettings


async def _enable_completeness(async_client: AsyncClient, headers: dict, **extra):
    payload = {
        "supported_languages": ["he", "en"],
        "default_language": "he",
        "require_product_completeness": True,
        **extra,
    }
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/settings",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _complete_product(slug: str, **overrides):
    body = {
        "name": {"en": "Complete Shirt", "he": "חולצה מלאה"},
        "slug": slug,
        "description": {"en": "Cotton shirt", "he": "חולצת כותנה"},
        "base_price": 40.00,
        "is_active": True,
        "variants": [{"sku": f"{slug.upper()}-M", "stock_quantity": 5}],
        "images": ["http://test.com/complete.png"],
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_store_admin_can_require_completeness(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    data = await _enable_completeness(async_client, headers)
    assert data["require_product_completeness"] is True
    assert data["force_product_completeness"] is False


@pytest.mark.asyncio
async def test_incomplete_active_product_rejected_when_required(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await _enable_completeness(async_client, headers)

    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json={
            "name": {"en": "Only English", "he": "רק עברית"},
            "slug": "incomplete-no-desc",
            "base_price": 12.00,
            "is_active": True,
            "variants": [{"sku": "INC-1", "stock_quantity": 3}],
            "images": ["http://test.com/img.png"],
        },
    )
    assert response.status_code == 422
    assert "cannot enter the store" in response.text
    assert "description" in response.text


@pytest.mark.asyncio
async def test_incomplete_draft_can_be_saved_when_required(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await _enable_completeness(async_client, headers)

    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json={
            "name": {"en": "Draft Shirt", "he": "חולצת טיוטה"},
            "slug": "draft-incomplete",
            "base_price": 12.00,
            "is_active": False,
            "variants": [{"sku": "DRAFT-1", "stock_quantity": 3}],
            "images": [],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["is_active"] is False

    public = await async_client.get("/api/v1/store/tenant-a/products/draft-incomplete")
    assert public.status_code == 404


@pytest.mark.asyncio
async def test_complete_product_enters_store_when_required(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await _enable_completeness(async_client, headers)

    created = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json=_complete_product("complete-when-required"),
    )
    assert created.status_code == 201, created.text

    public = await async_client.get("/api/v1/store/tenant-a/products/complete-when-required")
    assert public.status_code == 200
    assert public.json()["slug"] == "complete-when-required"


@pytest.mark.asyncio
async def test_enabling_completeness_removes_incomplete_seed_products(
    async_client: AsyncClient, seed_tokens, db_session
):
    public_before = await async_client.get("/api/v1/store/tenant-a/products")
    assert public_before.status_code == 200
    assert any(p["slug"] == "product-a1" for p in public_before.json()["data"])

    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await _enable_completeness(async_client, headers)

    product = (await db_session.execute(select(Product).where(Product.slug == "product-a1"))).scalar_one()
    assert product.is_active is False

    public_after = await async_client.get("/api/v1/store/tenant-a/products")
    assert all(p["slug"] != "product-a1" for p in public_after.json()["data"])


@pytest.mark.asyncio
async def test_update_cannot_publish_incomplete_product(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await _enable_completeness(async_client, headers)

    created = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json=_complete_product("publish-later", is_active=False, images=[]),
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    blocked = await async_client.put(
        f"/api/v1/admin/store/tenant-a/products/{product_id}",
        headers=headers,
        json={"is_active": True},
    )
    assert blocked.status_code == 422
    assert "cannot enter the store" in blocked.text


@pytest.mark.asyncio
async def test_nav_labels_must_cover_all_languages_when_completeness_required(
    async_client: AsyncClient, seed_tokens
):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/settings",
        headers=headers,
        json={
            "supported_languages": ["he", "en"],
            "default_language": "he",
            "require_product_completeness": True,
            "nav_items": [
                {"id": "home", "enabled": True, "kind": "home", "label": {"he": "בית"}},
            ],
        },
    )
    assert response.status_code == 422
    assert "Missing required translations" in response.text


@pytest.mark.asyncio
async def test_super_admin_can_force_completeness_and_store_cannot_disable(
    async_client: AsyncClient, seed_tokens, db_session
):
    super_headers = {"Authorization": seed_tokens["super_admin"]}
    forced = await async_client.patch(
        "/api/v1/super-admin/tenants/1/completeness",
        headers=super_headers,
        json={"force_product_completeness": True},
    )
    assert forced.status_code == 200, forced.text
    assert forced.json()["force_product_completeness"] is True

    db_session.expire_all()
    settings = (await db_session.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == 1)
    )).scalar_one()
    assert settings.force_product_completeness is True

    store_headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    ignored = await async_client.put(
        "/api/v1/admin/store/tenant-a/settings",
        headers=store_headers,
        json={"require_product_completeness": False},
    )
    assert ignored.status_code == 200, ignored.text
    assert ignored.json()["force_product_completeness"] is True

    blocked = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=store_headers,
        json={
            "name": {"en": "Forced Incomplete", "he": "לא מלא"},
            "slug": "forced-incomplete",
            "base_price": 12.00,
            "is_active": True,
            "variants": [{"sku": "FORCE-1", "stock_quantity": 1}],
            "images": ["http://test.com/img.png"],
        },
    )
    assert blocked.status_code == 422
    assert "cannot enter the store" in blocked.text

    listed = await async_client.get("/api/v1/super-admin/tenants", headers=super_headers)
    tenant = next(t for t in listed.json()["data"] if t["id"] == 1)
    assert tenant["force_product_completeness"] is True


@pytest.mark.asyncio
async def test_tenant_admin_cannot_set_force_flag(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.patch(
        "/api/v1/super-admin/tenants/1/completeness",
        headers=headers,
        json={"force_product_completeness": True},
    )
    assert response.status_code == 403
