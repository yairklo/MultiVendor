import hashlib
import hmac
import json
import time
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.models.order import Order


def _sign_stripe_payload(payload: str, secret: str) -> str:
    # Mirrors stripe.WebhookSignature._compute_signature -- a pure local
    # HMAC, no network call, so this is fully testable without a real
    # Stripe account.
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    sig = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


async def _checkout_one_item(async_client: AsyncClient, headers: dict) -> dict:
    cart_id = str(uuid.uuid4())
    add_resp = await async_client.post(
        "/api/v1/store/tenant-a/cart/" + cart_id + "/items", json={"variant_id": 1, "quantity": 1}
    )
    headers = {**headers, "X-Cart-Token": add_resp.json()["cart_token"]}
    payload = {
        "cart_id": cart_id,
        "coupon_code": None,
        "shipping_address": {"city": "Tel Aviv"},
        "payment_token": str(uuid.uuid4()),
    }
    response = await async_client.post("/api/v1/store/tenant-a/cart/checkout", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stripe_webhook_valid_signature_marks_order_processing(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    # Simulate an intent already having been created against this order by
    # an earlier /pay call (not exercised here -- that's covered separately
    # below with stripe.PaymentIntent.create mocked out).
    await db_session.execute(
        Order.__table__.update().where(Order.id == order["id"]).values(payment_intent_id="pi_test_123")
    )
    await db_session.commit()

    payload = json.dumps({
        "id": "evt_test_1",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test_123"}},
    })
    signature = _sign_stripe_payload(payload, "whsec_test_secret")

    response = await async_client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert response.status_code == 200

    refreshed = (await db_session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
    assert refreshed.status == "processing"


@pytest.mark.asyncio
async def test_stripe_webhook_wrong_signature_does_not_mark_paid(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)
    await db_session.execute(
        Order.__table__.update().where(Order.id == order["id"]).values(payment_intent_id="pi_test_456")
    )
    await db_session.commit()

    payload = json.dumps({
        "id": "evt_test_2",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_test_456"}},
    })
    # Signed with a secret that does NOT match settings.STRIPE_WEBHOOK_SECRET.
    signature = _sign_stripe_payload(payload, "whsec_wrong_secret")

    response = await async_client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert response.status_code == 400

    refreshed = (await db_session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
    assert refreshed.status == "pending_payment"


@pytest.mark.asyncio
async def test_stripe_webhook_missing_signature_header_rejected(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    payload = json.dumps({"id": "evt_x", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_x"}}})
    response = await async_client.post(
        "/api/v1/payments/webhook/stripe", content=payload, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_ignores_unrelated_event_type(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    # payment_intent.payment_failed must NOT flip the order to processing --
    # only a genuine .succeeded event does.
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)
    await db_session.execute(
        Order.__table__.update().where(Order.id == order["id"]).values(payment_intent_id="pi_test_789")
    )
    await db_session.commit()

    payload = json.dumps({
        "id": "evt_test_3",
        "type": "payment_intent.payment_failed",
        "data": {"object": {"id": "pi_test_789"}},
    })
    signature = _sign_stripe_payload(payload, "whsec_test_secret")

    response = await async_client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert response.status_code == 200

    refreshed = (await db_session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
    assert refreshed.status == "pending_payment"


@pytest.mark.asyncio
async def test_stripe_webhook_unknown_payment_intent_is_a_noop(async_client: AsyncClient, monkeypatch):
    # A signature-valid event for a payment_intent this app never created
    # (e.g. test traffic on a shared Stripe account) must not 500 -- just
    # nothing to update.
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    payload = json.dumps({
        "id": "evt_test_unknown",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_never_seen"}},
    })
    signature = _sign_stripe_payload(payload, "whsec_test_secret")

    response = await async_client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# /pay in stripe mode: starts a PaymentIntent, does NOT mark the order paid
# ---------------------------------------------------------------------------

class _FakeIntent:
    def __init__(self, id_: str, client_secret: str):
        self.id = id_
        self.client_secret = client_secret


@pytest.mark.asyncio
async def test_pay_order_stripe_mode_returns_client_secret_without_marking_paid(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_PUBLISHABLE_KEY", "pk_test_fake")
    monkeypatch.setattr(
        stripe.PaymentIntent, "create",
        staticmethod(lambda **kwargs: _FakeIntent("pi_fake_1", "pi_fake_1_secret_abc")),
    )

    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    response = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending_payment"  # NOT processing -- webhook hasn't confirmed anything
    assert body["payment"]["provider"] == "stripe"
    assert body["payment"]["client_secret"] == "pi_fake_1_secret_abc"
    assert body["payment"]["publishable_key"] == "pk_test_fake"

    refreshed = (await db_session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
    assert refreshed.status == "pending_payment"
    assert refreshed.payment_intent_id == "pi_fake_1"


@pytest.mark.asyncio
async def test_pay_order_mock_mode_unchanged(async_client: AsyncClient, seed_tokens):
    # Default PAYMENT_PROVIDER (no monkeypatch) -- must be completely
    # unaffected by the stripe integration existing at all.
    assert settings.PAYMENT_PROVIDER == "mock"
    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    response = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["payment"] is None


@pytest.mark.asyncio
async def test_pay_master_order_stripe_mode_one_intent_covers_every_sub_order(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(
        stripe.PaymentIntent, "create",
        staticmethod(lambda **kwargs: _FakeIntent("pi_fake_master_1", "pi_fake_master_1_secret")),
    )

    headers = {"Authorization": seed_tokens["customer_a"]}
    cart_id = str(uuid.uuid4())
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 1, "quantity": 1}, headers=headers)
    await async_client.post(f"/api/v1/marketplace/cart/{cart_id}/items", json={"variant_id": 2, "quantity": 1}, headers=headers)
    checkout = await async_client.post(
        "/api/v1/marketplace/checkout",
        json={"cart_id": cart_id, "shipping_address": {"city": "Tel Aviv"}, "payment_token": str(uuid.uuid4())},
        headers=headers,
    )
    assert checkout.status_code == 201
    master = checkout.json()

    response = await async_client.post(f"/api/v1/marketplace/orders/{master['id']}/pay", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["payment"]["client_secret"] == "pi_fake_master_1_secret"
    # Neither vendor's sub-order is paid yet -- only the shared webhook confirmation can do that.
    assert all(so["status"] == "pending_payment" for so in body["sub_orders"])

    # Firing the (signature-verified) webhook for that one intent pays both vendors at once.
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")
    payload = json.dumps({
        "id": "evt_master_1",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_fake_master_1"}},
    })
    signature = _sign_stripe_payload(payload, "whsec_test_secret")
    webhook_resp = await async_client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert webhook_resp.status_code == 200

    # Verified through the API (its own fresh DB session/transaction) rather
    # than db_session, which already holds an older snapshot from the read
    # above and would show stale pre-webhook state under MySQL's default
    # REPEATABLE READ isolation.
    final = await async_client.get(f"/api/v1/marketplace/orders/{master['id']}", headers=headers)
    assert final.status_code == 200
    assert all(so["status"] == "processing" for so in final.json()["sub_orders"])
