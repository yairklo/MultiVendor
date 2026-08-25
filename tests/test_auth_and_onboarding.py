import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_tenant_success(async_client: AsyncClient, db_session):
    payload = {
        "store_name": "New Store",
        "store_slug": "new-store",
        "admin_email": "admin@newstore.com",
        "admin_password": "securepassword123",
        "admin_full_name": "John Doe",
        "plan_code": "free"
    }
    response = await async_client.post("/api/v1/auth/register-tenant", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    # Global role is only ever 'super_admin' or 'user' now -- being this new
    # store's tenant_admin is recorded on UserStoreMembership, not here.
    assert data["role"] == "user"

@pytest.mark.asyncio
async def test_register_tenant_existing_customer_becomes_admin_with_correct_password(async_client: AsyncClient, db_session):
    payload = {
        "store_name": "Yet Another Store",
        "store_slug": "yet-another-store",
        "admin_email": "customer@gmail.com",
        "admin_password": "password",
        "admin_full_name": "Someone",
        "plan_code": "free"
    }
    response = await async_client.post("/api/v1/auth/register-tenant", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"
    assert data["store_role"] == "tenant_admin"
    assert data["access_token"] != data["refresh_token"]

    admin_headers = {"Authorization": f"Bearer {data['access_token']}"}
    orders = await async_client.get("/api/v1/admin/store/yet-another-store/orders", headers=admin_headers)
    assert orders.status_code == 200

@pytest.mark.asyncio
async def test_register_tenant_existing_email_rejects_wrong_password(async_client: AsyncClient, db_session):
    payload = {
        "store_name": "Yet Another Store",
        "store_slug": "yet-another-store",
        "admin_email": "customer@gmail.com",
        "admin_password": "securepassword123",
        "admin_full_name": "Someone",
        "plan_code": "free"
    }
    response = await async_client.post("/api/v1/auth/register-tenant", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_register_tenant_duplicate_slug_conflict(async_client: AsyncClient, db_session):
    payload = {
        "store_name": "Store A",
        "store_slug": "tenant-a",
        "admin_email": "admin2@tenanta.com",
        "admin_password": "securepassword123",
        "admin_full_name": "Jane Doe",
        "plan_code": "free"
    }
    response = await async_client.post("/api/v1/auth/register-tenant", json=payload)
    assert response.status_code == 409

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_payload", [
    {"store_name": "St", "store_slug": "valid-slug", "admin_email": "a@b.com", "admin_password": "secure123", "admin_full_name": "A", "plan_code": "free"}, # Name too short
    {"store_name": "Valid Name", "store_slug": "invalid slug!", "admin_email": "a@b.com", "admin_password": "secure123", "admin_full_name": "A", "plan_code": "free"}, # Invalid slug regex
    {"store_name": "Valid Name", "store_slug": "valid-slug", "admin_email": "not-an-email", "admin_password": "secure123", "admin_full_name": "A", "plan_code": "free"}, # Invalid email
    {"store_name": "Valid Name", "store_slug": "valid-slug", "admin_email": "a@b.com", "admin_password": "short", "admin_full_name": "A", "plan_code": "free"}, # Password too short
])
async def test_register_tenant_validation_failures(async_client: AsyncClient, db_session, invalid_payload):
    response = await async_client.post("/api/v1/auth/register-tenant", json=invalid_payload)
    assert response.status_code == 422 # FastAPI validation error

@pytest.mark.asyncio
async def test_login_super_admin_success(async_client: AsyncClient, db_session):
    payload = {
        "email": "superadmin@platform.com",
        "password": "password",
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "super_admin"
    assert body["access_token"] != body["refresh_token"]

    reused = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert reused.status_code == 200
    assert reused.json()["refresh_token"] != body["refresh_token"]

    replay = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert replay.status_code == 401

@pytest.mark.asyncio
async def test_login_tenant_admin_success(async_client: AsyncClient, db_session):
    # tenant_slug is accepted but no longer required or checked at login time
    # -- identity is global, store-level authorization is re-checked per
    # request (see deps.get_tenant_admin), not decided here.
    payload = {
        "email": "admin.store1@platform.com",
        "password": "password",
        "tenant_slug": "tenant-a"
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["role"] == "user"

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, db_session):
    payload = {
        "email": "admin.store1@platform.com",
        "password": "wrongpassword",
        "tenant_slug": "tenant-a"
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_without_tenant_slug_still_succeeds(async_client: AsyncClient, db_session):
    # A global account logs in exactly once, regardless of how many stores it
    # administers or shops at -- tenant_slug is not required to disambiguate
    # anymore (contrast with the old per-tenant-row identity model).
    payload = {
        "email": "admin.store1@platform.com",
        "password": "password",
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["role"] == "user"

@pytest.mark.asyncio
async def test_register_customer_under_tenant(async_client: AsyncClient, db_session):
    payload = {
        "email": "newcustomer@example.com",
        "password": "securepassword",
        "full_name": "New Customer"
    }
    response = await async_client.post("/api/v1/auth/register-customer/tenant-a", json=payload)
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_customer_email_uniqueness_is_global(async_client: AsyncClient, db_session):
    # customer@gmail.com already exists globally (seeded as a member of both
    # tenant-a and tenant-b) -- registering it "fresh" against a third store
    # must still conflict, since identity is global now, not per-tenant.
    payload = {
        "email": "customer@gmail.com",
        "password": "securepassword",
        "full_name": "Duplicate Customer"
    }
    response = await async_client.post("/api/v1/auth/register-customer/tenant-a", json=payload)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_register_customer_global_success(async_client: AsyncClient, db_session):
    payload = {
        "email": "marketplace-shopper@example.com",
        "password": "securepassword",
        "full_name": "Marketplace Shopper"
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "user"
    # Global signup has no store scope yet -- no membership was created.
    assert data["store_role"] is None

    # The account is immediately usable for a normal login, tenant_slug-free.
    login = await async_client.post("/api/v1/auth/login", json={
        "email": "marketplace-shopper@example.com",
        "password": "securepassword",
    })
    assert login.status_code == 200

@pytest.mark.asyncio
async def test_register_customer_global_duplicate_email_conflict(async_client: AsyncClient, db_session):
    # customer@gmail.com already exists globally in the seed data.
    payload = {
        "email": "customer@gmail.com",
        "password": "securepassword",
        "full_name": "Duplicate Shopper"
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_register_tenant_creates_default_settings(async_client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.tenant import Tenant, TenantSettings

    payload = {
        "store_name": "Settings Check Store",
        "store_slug": "settings-check-store",
        "admin_email": "admin@settingscheck.com",
        "admin_password": "securepassword123",
        "admin_full_name": "Settings Checker",
        "plan_code": "free"
    }
    response = await async_client.post("/api/v1/auth/register-tenant", json=payload)
    assert response.status_code == 201

    tenant = (await db_session.execute(
        select(Tenant).where(Tenant.slug == "settings-check-store")
    )).scalar_one()
    settings = (await db_session.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )).scalar_one_or_none()
    assert settings is not None
    assert settings.currency == "ILS"

@pytest.mark.asyncio
async def test_get_me_profile_authenticated_vs_unauthenticated(async_client: AsyncClient, seed_tokens):
    response = await async_client.get("/api/v1/customer/me")
    assert response.status_code == 401

    headers = {"Authorization": seed_tokens["customer_a"]}
    response = await async_client.get("/api/v1/customer/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert response.json()["email"] == "customer@gmail.com"
