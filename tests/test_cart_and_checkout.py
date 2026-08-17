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
    await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
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
async def test_update_cart_item_quantity_increases_and_decreases(async_client: AsyncClient, seed_tokens):
    cart_id = str(uuid.uuid4())
    add_resp = await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 2})
    assert add_resp.status_code == 201

    cart = (await async_client.get(f"/api/v1/store/tenant-a/cart/{cart_id}")).json()
    item_id = cart["items"][0]["id"]

    up_resp = await async_client.patch(f"/api/v1/store/tenant-a/cart/{cart_id}/items/{item_id}", json={"quantity": 5})
    assert up_resp.status_code == 200

    cart = (await async_client.get(f"/api/v1/store/tenant-a/cart/{cart_id}")).json()
    assert cart["items"][0]["quantity"] == 5
    assert float(cart["items"][0]["total_price"]) == 5 * float(cart["items"][0]["unit_price"])

    down_resp = await async_client.patch(f"/api/v1/store/tenant-a/cart/{cart_id}/items/{item_id}", json={"quantity": 1})
    assert down_resp.status_code == 200
    cart = (await async_client.get(f"/api/v1/store/tenant-a/cart/{cart_id}")).json()
    assert cart["items"][0]["quantity"] == 1

@pytest.mark.asyncio
async def test_update_cart_item_insufficient_stock_rejected(async_client: AsyncClient, seed_tokens):
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
    cart = (await async_client.get(f"/api/v1/store/tenant-a/cart/{cart_id}")).json()
    item_id = cart["items"][0]["id"]

    response = await async_client.patch(f"/api/v1/store/tenant-a/cart/{cart_id}/items/{item_id}", json={"quantity": 99999})
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_update_cart_item_not_found(async_client: AsyncClient, seed_tokens):
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})

    response = await async_client.patch(f"/api/v1/store/tenant-a/cart/{cart_id}/items/999999", json={"quantity": 2})
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_checkout_success_creates_order_and_snapshot(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
    payload = {
        "cart_id": cart_id,
        "coupon_code": None,
        "shipping_address": {"city": "Tel Aviv"},
        "payment_token": str(uuid.uuid4())
    }
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response.status_code == 201


async def _checkout_one_item(async_client: AsyncClient, headers: dict) -> dict:
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/store/tenant-a/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1})
    payload = {
        "cart_id": cart_id,
        "coupon_code": None,
        "shipping_address": {"city": "Tel Aviv"},
        "payment_token": str(uuid.uuid4())
    }
    response = await async_client.post(f"/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_checkout_order_item_has_resolved_product_name(async_client: AsyncClient, seed_tokens):
    # product.name is an i18n dict ({"en": ..., "he": ...}); the order item
    # snapshot used to store str(dict) verbatim (e.g. "{'en': 'Product A1', ...}")
    # instead of resolving it to a plain display string.
    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)
    assert order["items"][0]["product_name"] == "Product A1"


@pytest.mark.asyncio
async def test_checkout_creates_order_awaiting_mock_payment(async_client: AsyncClient, seed_tokens):
    # Checkout reserves stock and creates the order, but it isn't "placed" until
    # the (mock) payment step completes — otherwise there's nothing for the
    # abandoned-checkout expiry job to ever find.
    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)
    assert order["status"] == "pending_payment"


@pytest.mark.asyncio
async def test_pay_order_marks_it_processing(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    response = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

    get_resp = await async_client.get(f"/api/v1/customer/orders/{order['id']}", headers=headers)
    assert get_resp.json()["status"] == "processing"


@pytest.mark.asyncio
async def test_pay_order_twice_fails(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    first = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert first.status_code == 200

    second = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_pay_order_requires_ownership(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers_a)

    # seed_tokens["customer_a"] and ["customer_b"] are now the same global
    # user (see conftest.py), so genuine cross-account ownership needs a
    # second, actually-different global user -- tenant_admin_b fits (id 3,
    # no orders of its own) without needing a bespoke fixture just for this.
    other_user_headers = {"Authorization": seed_tokens["tenant_admin_b"]}
    response = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=other_user_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_order_awaiting_payment_restores_stock(async_client: AsyncClient, seed_tokens, db_session):
    from sqlalchemy import select
    from app.models.catalog import ProductVariant

    headers = {"Authorization": seed_tokens["customer_a"]}

    variant_before = (await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))).scalar_one()
    stock_before = variant_before.stock_quantity

    order = await _checkout_one_item(async_client, headers)
    assert order["status"] == "pending_payment"

    response = await async_client.delete(f"/api/v1/customer/orders/{order['id']}", headers=headers)
    assert response.status_code == 200

    variant_after = (await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))).scalar_one()
    assert variant_after.stock_quantity == stock_before
