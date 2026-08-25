import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select

from app.models.order import Order, OrderItem
from app.models.shipping_config import TenantShippingConfig

HFD_BASE = "https://api.hfd.co.il/rest/v2"


async def _seed_processing_order(db_session, *, order_number: str, shipping_json: dict | None) -> Order:
    order = Order(
        tenant_id=1,
        user_id=4,
        order_number=order_number,
        subtotal=10.0,
        total_amount=10.0,
        status="processing",
        order_type="physical",
        shipping_json=shipping_json,
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(OrderItem(
        tenant_id=1, order_id=order.id, variant_id=1,
        product_name="Product A1", sku="SKU-A1-1", unit_price=10.0, quantity=2,
    ))
    await db_session.commit()
    return order


async def _seed_hfd_config(db_session, *, is_default: bool = True, auto_fulfill: bool = False) -> TenantShippingConfig:
    from app.core.crypto import encrypt_json

    config = TenantShippingConfig(
        tenant_id=1,
        provider="hfd",
        credentials_encrypted=encrypt_json({"auth_token": "test-token", "client_number": 999}),
        sender_name="Store A",
        sender_phone="03-1234567",
        sender_city="תל אביב",
        sender_street="הרצל",
        sender_house_number="1",
        is_active=True,
        is_default=is_default,
        auto_fulfill=auto_fulfill,
    )
    db_session.add(config)
    await db_session.commit()
    return config


async def _seed_pending_payment_order(
    db_session, *, order_number: str, order_type: str = "physical", shipping_json: dict | None
) -> Order:
    order = Order(
        tenant_id=1,
        user_id=4,
        order_number=order_number,
        subtotal=10.0,
        total_amount=10.0,
        status="pending_payment",
        order_type=order_type,
        shipping_json=shipping_json,
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(OrderItem(
        tenant_id=1, order_id=order.id, variant_id=1,
        product_name="Product A1", sku="SKU-A1-1", unit_price=10.0, quantity=2,
    ))
    await db_session.commit()
    return order


_COMPLETE_SHIPPING_JSON = {
    "full_name": "דנה כהן",
    "email": "dana@example.com",
    "phone": "0501234567",
    "city": "חיפה",
    "street": "הנביאים",
    "house_number": "22",
}


class TestShippingConfig:
    async def test_upsert_and_list_shipping_config(self, async_client: AsyncClient, seed_tokens):
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        payload = {
            "provider": "hfd",
            "credentials": {"auth_token": "abc", "client_number": 123},
            "sender_name": "Store A",
            "sender_phone": "03-1234567",
            "sender_city": "תל אביב",
            "sender_street": "הרצל",
            "sender_house_number": "1",
            "is_default": True,
        }
        put_response = await async_client.put(
            "/api/v1/admin/store/tenant-a/shipping-config", json=payload, headers=headers
        )
        assert put_response.status_code == 200
        body = put_response.json()
        assert body["provider"] == "hfd"
        assert body["is_default"] is True
        assert "credentials" not in body

        list_response = await async_client.get(
            "/api/v1/admin/store/tenant-a/shipping-config", headers=headers
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

    async def test_upsert_missing_credential_field_returns_422(self, async_client: AsyncClient, seed_tokens):
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        payload = {
            "provider": "hfd",
            "credentials": {"auth_token": "abc"},  # missing client_number
            "sender_name": "Store A",
            "sender_phone": "03-1234567",
            "sender_city": "תל אביב",
            "sender_street": "הרצל",
            "sender_house_number": "1",
        }
        response = await async_client.put(
            "/api/v1/admin/store/tenant-a/shipping-config", json=payload, headers=headers
        )
        assert response.status_code == 422
        assert "client_number" in response.json()["detail"]

    async def test_delete_shipping_config(self, async_client: AsyncClient, seed_tokens, db_session):
        await _seed_hfd_config(db_session)
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        delete_response = await async_client.delete(
            "/api/v1/admin/store/tenant-a/shipping-config/hfd", headers=headers
        )
        assert delete_response.status_code == 200

        result = await db_session.execute(select(TenantShippingConfig))
        assert result.scalars().first() is None

    async def test_non_admin_cannot_manage_shipping_config(self, async_client: AsyncClient, seed_tokens):
        headers = {"Authorization": seed_tokens["customer_a"]}
        response = await async_client.get(
            "/api/v1/admin/store/tenant-a/shipping-config", headers=headers
        )
        assert response.status_code == 403


class TestFulfillOrder:
    @respx.mock
    async def test_fulfill_order_success(self, async_client: AsyncClient, seed_tokens, db_session):
        await _seed_hfd_config(db_session)
        order = await _seed_processing_order(
            db_session, order_number="ORD-SHIP-1", shipping_json=_COMPLETE_SHIPPING_JSON
        )
        respx.post(f"{HFD_BASE}/shipments/create").mock(
            return_value=httpx.Response(200, json={"shipmentNumber": "9988776", "randNumber": "RAND1"})
        )

        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        response = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["tracking_number"] == "9988776"
        assert body["provider"] == "hfd"
        assert body["label_url"] == f"{HFD_BASE}/shipments/9988776/label"

        await db_session.refresh(order)
        assert order.status == "shipped"
        assert order.tracking_number == "9988776"
        assert order.shipping_provider == "hfd"

    async def test_fulfill_order_missing_shipping_fields_returns_422(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        await _seed_hfd_config(db_session)
        # Mirrors what checkout actually sends today (frontend/src/app/checkout/page.tsx):
        # only full_name/email/address_line_1 -- no city, no phone.
        order = await _seed_processing_order(
            db_session,
            order_number="ORD-SHIP-2",
            shipping_json={"full_name": "דנה כהן", "email": "dana@example.com", "address_line_1": "הנביאים 22"},
        )
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        response = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "city" in detail
        assert "phone" in detail

    async def test_fulfill_order_wrong_status_returns_422(self, async_client: AsyncClient, seed_tokens, db_session):
        await _seed_hfd_config(db_session)
        order = Order(
            tenant_id=1, user_id=4, order_number="ORD-SHIP-3", subtotal=10.0, total_amount=10.0,
            status="pending_payment", order_type="physical", shipping_json=_COMPLETE_SHIPPING_JSON,
        )
        db_session.add(order)
        await db_session.commit()

        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        response = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert response.status_code == 422
        assert "processing" in response.json()["detail"]

    async def test_fulfill_order_no_shipping_config_returns_422(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        order = await _seed_processing_order(
            db_session, order_number="ORD-SHIP-4", shipping_json=_COMPLETE_SHIPPING_JSON
        )
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        response = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert response.status_code == 422
        assert "no" in response.json()["detail"].lower() or "shipping provider" in response.json()["detail"].lower()

    @respx.mock
    async def test_fulfill_order_provider_error_returns_502(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        await _seed_hfd_config(db_session)
        order = await _seed_processing_order(
            db_session, order_number="ORD-SHIP-5", shipping_json=_COMPLETE_SHIPPING_JSON
        )
        respx.post(f"{HFD_BASE}/shipments/create").mock(
            return_value=httpx.Response(200, json={"errorMessage": "Invalid city name"})
        )

        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        response = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert response.status_code == 502
        assert "Invalid city name" in response.json()["detail"]

    @respx.mock
    async def test_fulfill_order_already_shipped_returns_422(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        await _seed_hfd_config(db_session)
        order = await _seed_processing_order(
            db_session, order_number="ORD-SHIP-6", shipping_json=_COMPLETE_SHIPPING_JSON
        )
        respx.post(f"{HFD_BASE}/shipments/create").mock(
            return_value=httpx.Response(200, json={"shipmentNumber": "1", "randNumber": "R"})
        )
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        first = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert first.status_code == 200

        second = await async_client.post(
            f"/api/v1/admin/store/tenant-a/orders/{order.id}/fulfill", headers=headers
        )
        assert second.status_code == 422
        assert "already" in second.json()["detail"].lower()


class TestAutoFulfillment:
    """maybe_auto_fulfill_order is wired into pay_order_service's mock-pay
    path (order_service.py) -- these exercise it end to end through
    POST /api/v1/customer/orders/{id}/pay, which is the only trigger that
    doesn't need a real Stripe webhook to test."""

    @respx.mock
    async def test_auto_fulfill_triggers_on_mock_pay(self, async_client: AsyncClient, seed_tokens, db_session):
        await _seed_hfd_config(db_session, auto_fulfill=True)
        order = await _seed_pending_payment_order(
            db_session, order_number="ORD-AUTO-1", shipping_json=_COMPLETE_SHIPPING_JSON
        )
        respx.post(f"{HFD_BASE}/shipments/create").mock(
            return_value=httpx.Response(200, json={"shipmentNumber": "555", "randNumber": "R"})
        )

        headers = {"Authorization": seed_tokens["customer"]}
        response = await async_client.post(f"/api/v1/customer/orders/{order.id}/pay", headers=headers)
        assert response.status_code == 200

        await db_session.refresh(order)
        assert order.status == "shipped"
        assert order.tracking_number == "555"
        assert order.shipping_provider == "hfd"

    @respx.mock
    async def test_auto_fulfill_disabled_by_default_does_not_trigger(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        # auto_fulfill defaults to False -- a configured courier alone must
        # not be enough to ship automatically.
        await _seed_hfd_config(db_session, auto_fulfill=False)
        order = await _seed_pending_payment_order(
            db_session, order_number="ORD-AUTO-2", shipping_json=_COMPLETE_SHIPPING_JSON
        )
        route = respx.post(f"{HFD_BASE}/shipments/create").mock(
            return_value=httpx.Response(200, json={"shipmentNumber": "555", "randNumber": "R"})
        )

        headers = {"Authorization": seed_tokens["customer"]}
        response = await async_client.post(f"/api/v1/customer/orders/{order.id}/pay", headers=headers)
        assert response.status_code == 200
        assert route.call_count == 0

        await db_session.refresh(order)
        assert order.status == "processing"
        assert order.tracking_number is None

    @respx.mock
    async def test_auto_fulfill_skips_digital_orders(self, async_client: AsyncClient, seed_tokens, db_session):
        # The core guarantee the user asked for: a seller with no shipping
        # configured at all (or a purely digital order) must be able to
        # sell and get paid with zero courier involvement.
        await _seed_hfd_config(db_session, auto_fulfill=True)
        order = await _seed_pending_payment_order(
            db_session, order_number="ORD-AUTO-3", order_type="digital", shipping_json=None
        )
        route = respx.post(f"{HFD_BASE}/shipments/create").mock(
            return_value=httpx.Response(200, json={"shipmentNumber": "555", "randNumber": "R"})
        )

        headers = {"Authorization": seed_tokens["customer"]}
        response = await async_client.post(f"/api/v1/customer/orders/{order.id}/pay", headers=headers)
        assert response.status_code == 200
        assert route.call_count == 0

        await db_session.refresh(order)
        assert order.status == "processing"
        assert order.tracking_number is None

    async def test_auto_fulfill_failure_does_not_break_payment(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        # No respx mock at all here -- any attempted HTTP call raises. Also
        # missing city/phone, so _extract_recipient would reject it even if
        # the call somehow succeeded. Either way, /pay must still return 200.
        await _seed_hfd_config(db_session, auto_fulfill=True)
        order = await _seed_pending_payment_order(
            db_session, order_number="ORD-AUTO-4", shipping_json={"full_name": "דנה כהן", "address_line_1": "הנביאים 22"}
        )

        headers = {"Authorization": seed_tokens["customer"]}
        response = await async_client.post(f"/api/v1/customer/orders/{order.id}/pay", headers=headers)
        assert response.status_code == 200

        await db_session.refresh(order)
        assert order.status == "processing"
        assert order.tracking_number is None

    async def test_seller_without_any_shipping_config_can_still_get_paid(
        self, async_client: AsyncClient, seed_tokens, db_session
    ):
        # No TenantShippingConfig row at all for this tenant -- the base
        # case of "sell without shipping ever being involved."
        order = await _seed_pending_payment_order(
            db_session, order_number="ORD-AUTO-5", order_type="digital", shipping_json=None
        )
        headers = {"Authorization": seed_tokens["customer"]}
        response = await async_client.post(f"/api/v1/customer/orders/{order.id}/pay", headers=headers)
        assert response.status_code == 200

        await db_session.refresh(order)
        assert order.status == "processing"


class TestShippingConfigAutoFulfillField:
    async def test_auto_fulfill_round_trips_through_config_api(self, async_client: AsyncClient, seed_tokens):
        headers = {"Authorization": seed_tokens["tenant_admin_a"]}
        payload = {
            "provider": "hfd",
            "credentials": {"auth_token": "abc", "client_number": 123},
            "sender_name": "Store A",
            "sender_phone": "03-1234567",
            "sender_city": "תל אביב",
            "sender_street": "הרצל",
            "sender_house_number": "1",
            "is_default": True,
            "auto_fulfill": True,
        }
        put_response = await async_client.put(
            "/api/v1/admin/store/tenant-a/shipping-config", json=payload, headers=headers
        )
        assert put_response.status_code == 200
        assert put_response.json()["auto_fulfill"] is True

        list_response = await async_client.get(
            "/api/v1/admin/store/tenant-a/shipping-config", headers=headers
        )
        assert list_response.json()[0]["auto_fulfill"] is True
