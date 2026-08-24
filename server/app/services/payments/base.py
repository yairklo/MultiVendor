from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class PaymentIntentResult:
    # provider_ref is the provider's own id for this payment (e.g. Stripe's
    # PaymentIntent id, "pi_..."). Stored on Order.payment_intent_id /
    # MasterOrder.payment_intent_id so the webhook can look up which order a
    # confirmation event belongs to.
    provider_ref: str
    client_secret: str
    publishable_key: Optional[str]
    # Provider-native status string (e.g. Stripe's "requires_payment_method",
    # "requires_confirmation", "succeeded", "canceled"). Used by callers
    # deciding whether an existing provider_ref can still be reused
    # (retrieve_payment_intent) or is dead and needs a fresh one.
    status: str


@dataclass
class WebhookEvent:
    provider_ref: str
    succeeded: bool
    # Smallest-currency-unit amount and lowercase currency code as reported
    # BY THE PROVIDER on the event itself -- lets the caller cross-check
    # against the order's own total before trusting "succeeded" (see
    # order_service.mark_order_paid_by_payment_intent).
    amount: int
    currency: str


class WebhookVerificationError(Exception):
    """Raised when a webhook payload's signature does not verify against the
    configured secret -- the payload must never be trusted (order marked
    paid, etc.) without this passing first."""


# Every currency this app is expected to use (ILS, USD, EUR, ...) has 2
# minor-unit digits -- none are zero-decimal currencies like JPY -- so *100
# is correct here without a currency-specific exponent table. Shared by
# every provider's create_payment_intent and by the webhook amount check in
# order_service.mark_order_paid_by_payment_intent, so the two can never
# silently drift apart.
def to_smallest_unit(amount: Decimal, currency: str) -> int:
    return int((amount * 100).to_integral_value())


def amount_matches(order_amount: Decimal, reported_amount: int, reported_currency: str, expected_currency: str) -> bool:
    return (
        reported_amount == to_smallest_unit(order_amount, expected_currency)
        and reported_currency.lower() == expected_currency.lower()
    )


class PaymentProvider(ABC):
    """
    One real payment gateway's implementation of the operations the app
    actually needs: start a payment (idempotently), look one up again,
    cancel one, and find out (via a verified webhook, never a
    client-reported "it worked") whether it succeeded. Adding a second
    gateway (e.g. PayPlus) means implementing this interface once more and
    switching PAYMENT_PROVIDER -- nothing above this layer (order_service,
    marketplace_service, tasks.py, the webhook router) needs to change.
    """

    @abstractmethod
    async def create_payment_intent(
        self, *, amount: Decimal, currency: str, reference: str, metadata: dict, idempotency_key: str
    ) -> PaymentIntentResult:
        ...

    @abstractmethod
    async def retrieve_payment_intent(self, provider_ref: str) -> PaymentIntentResult:
        ...

    @abstractmethod
    async def cancel_payment_intent(self, provider_ref: str) -> None:
        ...

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature_header: str) -> WebhookEvent:
        ...
