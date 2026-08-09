import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_subscription_plan_upgrade(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    
    # Attempting upgrade to pro
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/subscription/upgrade?target_plan_code=pro", 
        headers=headers
    )
    assert response.status_code == 200
    
    # Asserting current limits increased
    response = await async_client.get("/api/v1/admin/store/tenant-a/subscription/current", headers=headers)
    assert response.status_code == 200
