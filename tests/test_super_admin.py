import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_super_admin_list_and_suspend_tenants(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}
    
    # 1. List tenants
    response = await async_client.get("/api/v1/super-admin/tenants", headers=headers)
    assert response.status_code == 200
    assert "data" in response.json()
    
    # 2. Suspend tenant
    response = await async_client.patch("/api/v1/super-admin/tenants/1/status?status=suspended", headers=headers)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_super_admin_audit_logs(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}
    response = await async_client.get("/api/v1/super-admin/audit-logs", headers=headers)
    assert response.status_code == 200
    assert "data" in response.json()
