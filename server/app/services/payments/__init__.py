from decimal import Decimal
from typing import Optional

from app.core.config import settings
from .base import PaymentProvider, PaymentIntentResult, WebhookEvent, WebhookVerificationError
from .stripe_provider import StripePaymentProvider

__all__ = [
    "PaymentProvider", "PaymentIntentResult", "WebhookEvent", "WebhookVerificationError",
    "StripePaymentProvider", "get_payment_provider", "get_or_create_payment_intent",
]

# Terminal state: a canceled intent can never be confirmed, so reusing its id
# would hand the frontend a client_secret that can only ever fail. Every
# other status (including "succeeded", reached if a client retries /pay
# after the webhook already landed) is safe to just hand back as-is.
_DEAD_STATUSES = {"canceled"}


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "stripe":
        return StripePaymentProvider()
    raise ValueError(
        f"No real payment provider is configured for PAYMENT_PROVIDER={settings.PAYMENT_PROVIDER!r}"
    )


async def get_or_create_payment_intent(
    provider: PaymentProvider,
    *,
    existing_provider_ref: Optional[str],
    amount: Decimal,
    currency: str,
    reference: str,
    metadata: dict,
    idempotency_key: str,
) -> PaymentIntentResult:
    """
    Idempotent /pay: a double-click, a client timeout-and-retry, or a page
    refresh must never start a second charge for the same order. If a
    provider_ref is already on the order/master_order and still usable,
    reuse it (Stripe: retrieve, not create); only mint a fresh one when
    there's none yet or the old one is dead (e.g. canceled by
    cleanup_abandoned_checkouts). Shared by order_service and
    marketplace_service so this policy lives in exactly one place, not
    re-decided per caller.
    """
    if existing_provider_ref:
        existing = await provider.retrieve_payment_intent(existing_provider_ref)
        if existing.status not in _DEAD_STATUSES:
            return existing

    return await provider.create_payment_intent(
        amount=amount, currency=currency, reference=reference, metadata=metadata,
        idempotency_key=idempotency_key,
    )
