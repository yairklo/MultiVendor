import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import redis_client
from app.models.catalog import ProductVariant
from app.models.order import Order, OrderItem, MasterOrder
from app.services.tasks import cleanup_abandoned_checkouts


def _smallest_unit(total_amount) -> int:
    # Mirrors app.services.payments.base.to_smallest_unit -- every currency
    # this app uses (including the "ils" test default) has 2 minor-unit
    # digits.
    return int((Decimal(str(total_amount)) * 100).to_integral_value())


async def _seed_pending_order(
    db_session, *, age: timedelta, payment_intent_id: str | None = None, master_order_id: int | None = None,
    order_number: str,
) -> Order:
    order = Order(
        tenant_id=1,
        user_id=4,
        order_number=order_number,
        subtotal=10.0,
        total_amount=10.0,
        status="pending_payment",
        payment_intent_id=payment_intent_id,
        master_order_id=master_order_id,
        created_at=(datetime.now(timezone.utc) - age).replace(tzinfo=None),
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(OrderItem(
        tenant_id=1, order_id=order.id, variant_id=1,
        product_name="Product A1", sku="SKU-A1-1", unit_price=10.0, quantity=2,
    ))
    await redis_client.set(f"lock:order:{order.id}", "locked", ex=3600)
    await db_session.commit()
    return order


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
    await async_client.post(
        "/api/v1/store/tenant-a/cart/" + cart_id + "/items", json={"variant_id": 1, "quantity": 1}
    )
    # The cart's capability token (an HttpOnly cart_token cookie) is carried
    # automatically by this same client on the checkout call below.
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
        "data": {"object": {
            "id": "pi_test_123",
            "amount": _smallest_unit(order["total_amount"]),
            "currency": settings.STRIPE_CURRENCY,
        }},
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
        "data": {"object": {
            "id": "pi_test_456",
            "amount": _smallest_unit(order["total_amount"]),
            "currency": settings.STRIPE_CURRENCY,
        }},
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
        "data": {"object": {
            "id": "pi_test_789",
            "amount": _smallest_unit(order["total_amount"]),
            "currency": settings.STRIPE_CURRENCY,
        }},
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
        "data": {"object": {"id": "pi_never_seen", "amount": 1000, "currency": "ils"}},
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
    def __init__(self, id_: str, client_secret: str, status: str = "requires_payment_method"):
        self.id = id_
        self.client_secret = client_secret
        self.status = status


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
async def test_pay_order_stripe_mode_is_idempotent_on_repeat_calls(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    # A double-click, a client timeout-and-retry, or a page refresh on /pay
    # must reuse the existing PaymentIntent (retrieve), never mint a second
    # one -- otherwise the customer could be charged twice and the first
    # PI's eventual webhook would find nothing left to update.
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_PUBLISHABLE_KEY", "pk_test_fake")

    create_calls = []
    retrieve_calls = []
    monkeypatch.setattr(
        stripe.PaymentIntent, "create",
        staticmethod(lambda **kwargs: create_calls.append(kwargs) or _FakeIntent("pi_once", "pi_once_secret")),
    )
    monkeypatch.setattr(
        stripe.PaymentIntent, "retrieve",
        staticmethod(lambda ref, **kwargs: retrieve_calls.append(ref) or _FakeIntent("pi_once", "pi_once_secret")),
    )

    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    first = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    second = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["payment"]["client_secret"] == second.json()["payment"]["client_secret"] == "pi_once_secret"

    assert len(create_calls) == 1
    # Stripe's own idempotency_key must also be set on that one create call
    # (belt-and-suspenders alongside the app-level reuse above).
    assert create_calls[0]["idempotency_key"] == f"order:{order['id']}"
    assert retrieve_calls == ["pi_once"]

    refreshed = (await db_session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
    assert refreshed.payment_intent_id == "pi_once"
    assert refreshed.status == "pending_payment"


@pytest.mark.asyncio
async def test_pay_order_stripe_mode_creates_fresh_intent_if_old_one_canceled(
    async_client: AsyncClient, seed_tokens, db_session, monkeypatch
):
    # The old PaymentIntent might have been canceled by
    # cleanup_abandoned_checkouts (see tasks.py) -- a canceled intent can
    # never be confirmed, so /pay must mint a genuinely new one rather than
    # handing the frontend a client_secret that can only fail.
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")

    create_ids = iter(["pi_first", "pi_second"])
    create_calls = []

    def fake_create(**kwargs):
        create_calls.append(kwargs)
        pid = next(create_ids)
        return _FakeIntent(pid, f"{pid}_secret")

    monkeypatch.setattr(stripe.PaymentIntent, "create", staticmethod(fake_create))
    # Always reports "canceled" -- simulates cleanup_abandoned_checkouts
    # having canceled whatever PI is looked up.
    monkeypatch.setattr(
        stripe.PaymentIntent, "retrieve",
        staticmethod(lambda ref, **kwargs: _FakeIntent(ref, f"{ref}_secret", status="canceled")),
    )

    headers = {"Authorization": seed_tokens["customer_a"]}
    order = await _checkout_one_item(async_client, headers)

    first = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert first.status_code == 200
    assert first.json()["payment"]["client_secret"] == "pi_first_secret"

    second = await async_client.post(f"/api/v1/customer/orders/{order['id']}/pay", headers=headers)
    assert second.status_code == 200
    assert second.json()["payment"]["client_secret"] == "pi_second_secret"

    assert len(create_calls) == 2
    refreshed = (await db_session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
    assert refreshed.payment_intent_id == "pi_second"


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
        "data": {"object": {
            "id": "pi_fake_master_1",
            "amount": _smallest_unit(master["total_amount"]),
            "currency": settings.STRIPE_CURRENCY,
        }},
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


# ---------------------------------------------------------------------------
# cleanup_abandoned_checkouts: must not release stock out from under an open
# Stripe PaymentIntent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_leaves_stripe_order_alone_within_grace_window(db_session, monkeypatch):
    # 20 minutes old -- past the 15-minute mock timeout, but nowhere near the
    # 24-hour grace window a real open PaymentIntent gets.
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    order = await _seed_pending_order(
        db_session, age=timedelta(minutes=20), payment_intent_id="pi_open_1", order_number="ORD-CLEANUP-1",
    )

    await cleanup_abandoned_checkouts(db_session)

    refreshed = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == "pending_payment"


@pytest.mark.asyncio
async def test_cleanup_cancels_intent_then_expires_after_stripe_grace_window(db_session, monkeypatch):
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    canceled = []
    monkeypatch.setattr(
        stripe.PaymentIntent, "cancel",
        staticmethod(lambda ref, **kwargs: canceled.append(ref)),
    )

    order = await _seed_pending_order(
        db_session, age=timedelta(hours=25), payment_intent_id="pi_stale_1", order_number="ORD-CLEANUP-2",
    )
    variant_before = (await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))).scalar_one()
    stock_before = variant_before.stock_quantity

    await cleanup_abandoned_checkouts(db_session)

    assert canceled == ["pi_stale_1"]  # canceled on Stripe's side BEFORE releasing stock
    refreshed = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == "expired"
    variant_after = (await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))).scalar_one()
    assert variant_after.stock_quantity == stock_before + 2


@pytest.mark.asyncio
async def test_cleanup_does_not_expire_order_if_cancel_fails(db_session, monkeypatch):
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")

    def failing_cancel(ref, **kwargs):
        raise RuntimeError("network blip talking to Stripe")

    monkeypatch.setattr(stripe.PaymentIntent, "cancel", staticmethod(failing_cancel))

    order = await _seed_pending_order(
        db_session, age=timedelta(hours=25), payment_intent_id="pi_stale_2", order_number="ORD-CLEANUP-3",
    )
    variant_before = (await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))).scalar_one()
    stock_before = variant_before.stock_quantity

    # Must not raise -- one order's cancel failure can't take down the whole sweep.
    await cleanup_abandoned_checkouts(db_session)

    refreshed = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == "pending_payment"  # NOT expired -- couldn't confirm the charge is dead
    variant_after = (await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))).scalar_one()
    assert variant_after.stock_quantity == stock_before  # stock NOT released


@pytest.mark.asyncio
async def test_cleanup_cancels_marketplace_intent_once_for_all_sub_orders(db_session, monkeypatch):
    import stripe

    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    canceled = []
    monkeypatch.setattr(
        stripe.PaymentIntent, "cancel",
        staticmethod(lambda ref, **kwargs: canceled.append(ref)),
    )

    master_order = MasterOrder(
        user_id=4, master_order_number="MO-CLEANUP-1", total_amount=20.0, payment_intent_id="pi_master_stale",
    )
    db_session.add(master_order)
    await db_session.flush()
    master_id = master_order.id

    sub1 = await _seed_pending_order(db_session, age=timedelta(hours=25), master_order_id=master_id, order_number="ORD-CLEANUP-4A")
    sub2 = await _seed_pending_order(db_session, age=timedelta(hours=25), master_order_id=master_id, order_number="ORD-CLEANUP-4B")

    await cleanup_abandoned_checkouts(db_session)

    # One shared PaymentIntent for both vendors -- canceled exactly once, not per sub-order.
    assert canceled == ["pi_master_stale"]

    refreshed_sub1 = (await db_session.execute(select(Order).where(Order.id == sub1.id))).scalar_one()
    refreshed_sub2 = (await db_session.execute(select(Order).where(Order.id == sub2.id))).scalar_one()
    assert refreshed_sub1.status == "expired"
    assert refreshed_sub2.status == "expired"


@pytest.mark.asyncio
async def test_cleanup_mock_mode_order_still_expires_at_15_minutes(db_session):
    # Default PAYMENT_PROVIDER (no monkeypatch) -- unaffected by any of the
    # stripe-aware branching above.
    assert settings.PAYMENT_PROVIDER == "mock"
    order = await _seed_pending_order(db_session, age=timedelta(minutes=20), order_number="ORD-CLEANUP-5")

    await cleanup_abandoned_checkouts(db_session)

    refreshed = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == "expired"


# ---------------------------------------------------------------------------
# Webhook succeeding for an already-expired order must not silently flip it
# to 'processing' -- see order_service.mark_order_paid_by_payment_intent.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_webhook_success_for_already_expired_order_does_not_mark_processing(
    async_client: AsyncClient, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    order = await _seed_pending_order(
        db_session, age=timedelta(hours=25), payment_intent_id="pi_raced", order_number="ORD-CLEANUP-6",
    )
    # Simulate cleanup having already expired it (its cancel/expire path is
    # covered separately above) -- this test is specifically about the
    # webhook's own behavior once that's already happened.
    order.status = "expired"
    await db_session.commit()

    payload = json.dumps({
        "id": "evt_raced",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_raced", "amount": 1000, "currency": settings.STRIPE_CURRENCY}},
    })
    signature = _sign_stripe_payload(payload, "whsec_test_secret")
    response = await async_client.post(
        "/api/v1/payments/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    # 200 (not a Stripe-retriable error) -- the event was understood, we
    # just deliberately chose not to act on it.
    assert response.status_code == 200

    refreshed = (await db_session.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == "expired"  # NOT flipped to processing
