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
    assert data["role"] == "tenant_admin"

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
        "email": "super@admin.com",
        "password": "password",
        "tenant_slug": None
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["role"] == "super_admin"

@pytest.mark.asyncio
async def test_login_tenant_admin_success(async_client: AsyncClient, db_session):
    payload = {
        "email": "admin@tenanta.com",
        "password": "password",
        "tenant_slug": "tenant-a"
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["role"] == "tenant_admin"

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, db_session):
    payload = {
        "email": "admin@tenanta.com",
        "password": "wrongpassword",
        "tenant_slug": "tenant-a"
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_missing_tenant_slug_for_tenant_admin(async_client: AsyncClient, db_session):
    payload = {
        "email": "admin@tenanta.com",
        "password": "password"
        # Missing tenant_slug should be 401/403 or logic error if they aren't super admin
    }
    response = await async_client.post("/api/v1/auth/login", json=payload)
    # Could be 401 or 422 depending on business logic handling of 'tenant_slug'
    assert response.status_code in (401, 403, 404)

@pytest.mark.asyncio
async def test_register_customer_under_tenant(async_client: AsyncClient, db_session):
    payload = {
        "email": "newcustomer@tenanta.com",
        "password": "securepassword",
        "full_name": "New Customer"
    }
    response = await async_client.post("/api/v1/auth/register-customer/tenant-a", json=payload)
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_customer_email_uniqueness_per_tenant(async_client: AsyncClient, db_session):
    payload = {
        "email": "customer@tenanta.com",
        "password": "securepassword",
        "full_name": "Duplicate Customer"
    }
    response = await async_client.post("/api/v1/auth/register-customer/tenant-a", json=payload)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_get_me_profile_authenticated_vs_unauthenticated(async_client: AsyncClient, seed_tokens):
    response = await async_client.get("/api/v1/customer/me")
    assert response.status_code == 401

    headers = {"Authorization": seed_tokens["customer_a"]}
    response = await async_client.get("/api/v1/customer/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "customer"
