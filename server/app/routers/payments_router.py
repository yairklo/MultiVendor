from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.services.order_service import mark_order_paid_by_payment_intent
from app.services.payments import StripePaymentProvider
from app.services.payments.base import WebhookVerificationError

payments_router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@payments_router.post(
    "/webhook/stripe",
    summary="Stripe Webhook",
    description=(
        "Receives payment confirmation events directly from Stripe. The request body is only "
        "trusted after its `Stripe-Signature` header verifies against STRIPE_WEBHOOK_SECRET -- "
        "nothing a client reports (not even a successful client-side confirmCardPayment call) "
        "is enough on its own to mark an order paid."
    ),
    responses={
        200: {"description": "Event processed (or intentionally ignored, e.g. an unrelated event type)."},
        400: {"description": "Missing or invalid Stripe-Signature -- payload was not trusted."},
    },
)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()

    # Instantiated directly (not via get_payment_provider(), which is
    # gated by the app-wide PAYMENT_PROVIDER toggle) -- this route's whole
    # identity is "the Stripe webhook", independent of which provider is
    # currently driving the customer-facing /pay endpoints.
    try:
        provider = StripePaymentProvider()
        event = provider.verify_webhook(payload, stripe_signature or "")
    except (RuntimeError, WebhookVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event.succeeded:
        await mark_order_paid_by_payment_intent(event.provider_ref, event.amount, event.currency, db)

    return {"status": "ok"}
