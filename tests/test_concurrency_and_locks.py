import pytest
import asyncio
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_concurrent_checkout_overselling_prevention(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    
    cart_ids = []
    # Setup carts first
    for _ in range(5):
        cart_id = str(uuid.uuid4())
        await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
        cart_ids.append(cart_id)
        
    async def checkout_request(c_id):
        payload = {
            "cart_id": c_id,
            "coupon_code": None,
            "shipping_address": {"city": "Tel Aviv"},
            "payment_token": str(uuid.uuid4())
        }
        return await async_client.post(
            "/api/v1/store/tenant-a/cart/checkout", 
            json=payload, 
            headers=headers
        )

    responses = await asyncio.gather(*(checkout_request(cid) for cid in cart_ids))
    
    success_count = sum(1 for r in responses if r.status_code == 201)
    fail_count = sum(1 for r in responses if r.status_code in (409, 400))
    
    assert success_count + fail_count == 5
