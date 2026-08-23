from app.core.config import settings
from .base import PaymentProvider, PaymentIntentResult, WebhookEvent, WebhookVerificationError
from .stripe_provider import StripePaymentProvider

__all__ = [
    "PaymentProvider", "PaymentIntentResult", "WebhookEvent", "WebhookVerificationError",
    "StripePaymentProvider", "get_payment_provider",
]


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "stripe":
        return StripePaymentProvider()
    raise ValueError(
        f"No real payment provider is configured for PAYMENT_PROVIDER={settings.PAYMENT_PROVIDER!r}"
    )
