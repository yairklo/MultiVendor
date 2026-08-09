import pytest
import asyncio
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_concurrent_checkout_overselling_prevention(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    
    # Simulating 5 concurrent requests
    async def checkout_request():
        cart_id = str(uuid.uuid4())
        await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
        payload = {
            "cart_id": cart_id,
            "coupon_code": None,
            "shipping_address": {"city": "Tel Aviv"},
            "payment_token": str(uuid.uuid4())
        }
        response = await async_client.post(
            "/api/v1/store/tenant-a/cart/checkout", 
            json=payload, 
            headers=headers
        )
        return response

    responses = await asyncio.gather(*(checkout_request() for _ in range(5)))
    
    success_count = sum(1 for r in responses if r.status_code == 201)
    fail_count = sum(1 for r in responses if r.status_code in (409, 400))
    
    # Assuming stock quantity = 1 for the variant in the mock DB
    assert success_count <= 1
    assert fail_count >= 4
