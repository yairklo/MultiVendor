import asyncio
from decimal import Decimal

import stripe

from app.core.config import settings
from .base import PaymentProvider, PaymentIntentResult, WebhookEvent, WebhookVerificationError, to_smallest_unit

# Event types that count as a successful payment. payment_intent.payment_failed
# and any other event are deliberately NOT treated as success -- an order stays
# 'pending_payment' (and eventually expires via cleanup_abandoned_checkouts)
# unless a succeeded event verifies.
_SUCCESS_EVENT_TYPES = {"payment_intent.succeeded"}


class StripePaymentProvider(PaymentProvider):
    # Deliberately does NOT require STRIPE_SECRET_KEY at construction time --
    # verify_webhook only needs STRIPE_WEBHOOK_SECRET (a pure local HMAC
    # check, no Stripe API call at all), and the webhook route instantiates
    # this class independently of whether outbound payment creation is even
    # configured. Only create_payment_intent needs the API key, so it's
    # checked there instead.

    def _require_api_key(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured")
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_payment_intent(
        self, *, amount: Decimal, currency: str, reference: str, metadata: dict, idempotency_key: str
    ) -> PaymentIntentResult:
        self._require_api_key()

        # stripe-python is synchronous (blocking network I/O); run it off the
        # event loop so one checkout doesn't stall every other request.
        # idempotency_key (e.g. "order:123") means a retried/duplicate POST
        # from the frontend (double-click, timeout-and-retry) with the same
        # key returns Stripe's *original* PaymentIntent instead of creating
        # a second charge -- this is Stripe's own idempotency mechanism, on
        # top of (not instead of) the app-level reuse in order_service.
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=to_smallest_unit(amount, currency),
            currency=currency.lower(),
            description=reference,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        return _to_result(intent)

    async def retrieve_payment_intent(self, provider_ref: str) -> PaymentIntentResult:
        self._require_api_key()
        intent = await asyncio.to_thread(stripe.PaymentIntent.retrieve, provider_ref)
        return _to_result(intent)

    async def cancel_payment_intent(self, provider_ref: str) -> None:
        self._require_api_key()
        try:
            await asyncio.to_thread(stripe.PaymentIntent.cancel, provider_ref)
        except stripe.InvalidRequestError:
            # Already canceled, already succeeded, or otherwise not
            # cancelable -- nothing left to do, not a failure of the caller's
            # cancel request.
            pass

    def verify_webhook(self, payload: bytes, signature_header: str) -> WebhookEvent:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise WebhookVerificationError("STRIPE_WEBHOOK_SECRET is not configured")
        try:
            event = stripe.Webhook.construct_event(
                payload, signature_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.SignatureVerificationError) as e:
            raise WebhookVerificationError(str(e)) from e

        payment_intent = event["data"]["object"]
        return WebhookEvent(
            provider_ref=payment_intent["id"],
            succeeded=event["type"] in _SUCCESS_EVENT_TYPES,
            amount=payment_intent["amount"],
            currency=payment_intent["currency"],
        )


def _to_result(intent) -> PaymentIntentResult:
    return PaymentIntentResult(
        provider_ref=intent.id,
        client_secret=intent.client_secret,
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
        status=intent.status,
    )


# Stripe amounts are integers in the currency's smallest unit (agorot for
# ILS, cents for USD) for every currency this app is expected to use --
# none of them are zero-decimal currencies (e.g. JPY), so *100 is correct
# here without a currency-specific exponent table.
def _to_smallest_unit(amount: Decimal, currency: str) -> int:
    return int((amount * 100).to_integral_value())
