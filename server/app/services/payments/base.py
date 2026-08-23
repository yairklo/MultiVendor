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


@dataclass
class WebhookEvent:
    provider_ref: str
    succeeded: bool


class WebhookVerificationError(Exception):
    """Raised when a webhook payload's signature does not verify against the
    configured secret -- the payload must never be trusted (order marked
    paid, etc.) without this passing first."""


class PaymentProvider(ABC):
    """
    One real payment gateway's implementation of the two operations the app
    actually needs: start a payment, and find out (via a verified webhook,
    never a client-reported "it worked") whether it succeeded. Adding a
    second gateway (e.g. PayPlus) means implementing this interface once
    more and switching PAYMENT_PROVIDER -- nothing above this layer
    (order_service, marketplace_service, the webhook router) needs to change.
    """

    @abstractmethod
    async def create_payment_intent(
        self, *, amount: Decimal, currency: str, reference: str, metadata: dict
    ) -> PaymentIntentResult:
        ...

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature_header: str) -> WebhookEvent:
        ...
