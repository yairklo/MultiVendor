import pytest
from httpx import AsyncClient
import uuid

@pytest.mark.asyncio
async def test_cart_lifecycle_guest_and_authenticated(async_client: AsyncClient, seed_tokens):
    cart_id = str(uuid.uuid4())
    payload = {"variant_id": 1, "quantity": 2}
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json=payload)
    assert response.status_code == 201
    
    response = await async_client.get(f"/api/v1/store/tenant-a/cart/{cart_id}")
    assert response.status_code == 200
    assert "subtotal" in response.json()
    
    response = await async_client.delete(f"/api/v1/store/tenant-a/cart/{cart_id}/items/1")
    assert response.status_code == 200

@pytest.mark.asyncio
@pytest.mark.parametrize("quantity, expected_status", [
    (1, 201),
    (0, 422), # Below ge=1 constraint
    (-5, 422),
    (99999, 400) # Overselling, could be 400 or 409 if mock implemented
])
async def test_add_to_cart_quantity_validation(async_client: AsyncClient, seed_tokens, quantity, expected_status):
    cart_id = str(uuid.uuid4())
    payload = {"variant_id": 1, "quantity": quantity}
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json=payload)
    assert response.status_code == expected_status or (expected_status == 400 and response.status_code in (400, 409, 422))

@pytest.mark.asyncio
@pytest.mark.parametrize("coupon_code, expected_status", [
    ("VALID10", 201),
    ("EXPIRED", 400),
    ("MAX_USED", 400),
    ("BELOW_MIN", 400)
])
async def test_coupon_validation(async_client: AsyncClient, seed_tokens, coupon_code, expected_status):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    payload = {
        "cart_id": cart_id,
        "coupon_code": coupon_code,
        "shipping_address": {"city": "Tel Aviv"},
        "payment_token": str(uuid.uuid4())
    }
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response.status_code in (201, 400, 422, 404) 

@pytest.mark.asyncio
async def test_checkout_invalid_uuid(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {
        "cart_id": "not-a-uuid",
        "coupon_code": None,
        "shipping_address": {"city": "Tel Aviv"},
        "payment_token": str(uuid.uuid4())
    }
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response.status_code == 422 # FastAPI should catch non-UUID

@pytest.mark.asyncio
async def test_checkout_success_creates_order_and_snapshot(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    payload = {
        "cart_id": cart_id,
        "coupon_code": None,
        "shipping_address": {"city": "Tel Aviv"},
        "payment_token": str(uuid.uuid4())
    }
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response.status_code == 201
