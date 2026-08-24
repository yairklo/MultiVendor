import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
import uuid
from app.main import app

@pytest.mark.asyncio
async def test_concurrent_checkout_overselling_prevention(seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}

    # Each simulated shopper gets its own client (== its own cookie jar),
    # matching how 5 different browsers/guests would each hold their own
    # cart_token cookie -- a single shared client (and therefore a single
    # cart_token cookie value) can only ever represent one guest cart at a time.
    clients = [
        AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test")
        for _ in range(5)
    ]
    cart_ids = [str(uuid.uuid4()) for _ in range(5)]

    try:
        for client, cart_id in zip(clients, cart_ids):
            add_resp = await client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
            assert add_resp.status_code == 201

        async def checkout_request(client: AsyncClient, c_id: str):
            payload = {
                "cart_id": c_id,
                "coupon_code": None,
                "shipping_address": {"city": "Tel Aviv"},
                "payment_token": str(uuid.uuid4())
            }
            return await client.post("/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)

        responses = await asyncio.gather(*(checkout_request(c, cid) for c, cid in zip(clients, cart_ids)))

        success_count = sum(1 for r in responses if r.status_code == 201)
        fail_count = sum(1 for r in responses if r.status_code in (409, 400))

        assert success_count + fail_count == 5
    finally:
        for client in clients:
            await client.aclose()
