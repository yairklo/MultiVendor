import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_super_admin_list_and_suspend_tenants(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}

    response = await async_client.get("/api/v1/super-admin/tenants", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    tenant = next(t for t in body["data"] if t["id"] == 1)
    assert tenant["slug"] == "tenant-a"
    assert tenant["plan_code"] == "free"
    assert tenant["product_count"] >= 1
    assert "stripe_connected" in tenant
    assert "created_at" in tenant

    filtered = await async_client.get("/api/v1/super-admin/tenants?status=active", headers=headers)
    assert filtered.status_code == 200
    assert all(t["status"] == "active" for t in filtered.json()["data"])

    response = await async_client.patch("/api/v1/super-admin/tenants/1/status?status=suspended", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "suspended"

    suspended = await async_client.get("/api/v1/super-admin/tenants?status=suspended", headers=headers)
    assert any(t["id"] == 1 for t in suspended.json()["data"])


@pytest.mark.asyncio
async def test_super_admin_audit_logs(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}
    await async_client.patch("/api/v1/super-admin/tenants/1/status?status=suspended", headers=headers)

    response = await async_client.get("/api/v1/super-admin/audit-logs", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert any(entry["action"] == "tenant.status" for entry in data)


@pytest.mark.asyncio
async def test_super_admin_overview_plans_users_orders(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}

    overview = await async_client.get("/api/v1/super-admin/overview", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["tenants_total"] >= 2
    assert body["products_total"] >= 1
    assert body["orders_total"] >= 1
    assert "gmv" in body
    assert "recent_tenants" in body
    assert "recent_orders" in body

    me = await async_client.get("/api/v1/super-admin/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "super_admin"

    plans = await async_client.get("/api/v1/super-admin/plans", headers=headers)
    assert plans.status_code == 200
    codes = {p["code"] for p in plans.json()["data"]}
    assert {"free", "pro", "enterprise"} <= codes

    users = await async_client.get("/api/v1/super-admin/users", headers=headers)
    assert users.status_code == 200
    emails = {u["email"] for u in users.json()["data"]}
    assert "superadmin@platform.com" in emails
    customer = next(u for u in users.json()["data"] if u["email"] == "customer@gmail.com")
    assert any(m["role"] == "customer" for m in customer["memberships"])

    orders = await async_client.get("/api/v1/super-admin/orders", headers=headers)
    assert orders.status_code == 200
    assert any(o["order_number"] == "ORD-001" for o in orders.json()["data"])


@pytest.mark.asyncio
async def test_super_admin_create_tenant_change_plan_and_marketplace(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}

    created = await async_client.post(
        "/api/v1/super-admin/tenants",
        json={
            "name": "Store C",
            "slug": "tenant-c",
            "plan_id": 1,
            "admin_email": "admin.store3@platform.com",
            "admin_full_name": "Store 3 Admin",
            "admin_password": "password1",
            "show_all_products_in_marketplace": True,
        },
        headers=headers,
    )
    assert created.status_code == 201
    tenant = created.json()
    assert tenant["slug"] == "tenant-c"
    assert tenant["plan_code"] == "free"
    assert tenant["show_all_products_in_marketplace"] is True

    duplicate = await async_client.post(
        "/api/v1/super-admin/tenants",
        json={
            "name": "Store C again",
            "slug": "tenant-c",
            "plan_id": 1,
            "admin_email": "admin.store3b@platform.com",
            "admin_full_name": "Other Admin",
            "admin_password": "password1",
        },
        headers=headers,
    )
    assert duplicate.status_code == 409

    plan = await async_client.post(
        f"/api/v1/super-admin/tenants/{tenant['id']}/subscription",
        json={"plan_id": 2},
        headers=headers,
    )
    assert plan.status_code == 200
    assert plan.json()["plan_id"] == 2

    market = await async_client.patch(
        f"/api/v1/super-admin/tenants/{tenant['id']}/marketplace",
        json={"show_all_products_in_marketplace": False},
        headers=headers,
    )
    assert market.status_code == 200
    assert market.json()["show_all_products_in_marketplace"] is False


@pytest.mark.asyncio
async def test_super_admin_can_deactivate_user_but_not_self(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}

    blocked = await async_client.patch(
        "/api/v1/super-admin/users/1/status",
        json={"is_active": False},
        headers=headers,
    )
    assert blocked.status_code == 400

    response = await async_client.patch(
        "/api/v1/super-admin/users/4/status",
        json={"is_active": False},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_tenant_admin_cannot_access_new_super_admin_routes(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    for path in (
        "/api/v1/super-admin/overview",
        "/api/v1/super-admin/plans",
        "/api/v1/super-admin/users",
        "/api/v1/super-admin/orders",
        "/api/v1/super-admin/me",
    ):
        response = await async_client.get(path, headers=headers)
        assert response.status_code == 403, path
