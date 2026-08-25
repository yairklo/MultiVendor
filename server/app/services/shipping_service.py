import logging
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from israel_shipping_sdk.exceptions import ShippingException
from israel_shipping_sdk.models import Address, Contact, Package, ShipmentRequest, ShipmentResponse

from app.core.crypto import decrypt_json, encrypt_json
from app.db.tenant_context import unscoped
from app.models.order import Order
from app.models.shipping_config import TenantShippingConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.shipping_schemas import (
    FulfillOrderResponse,
    TenantShippingConfigCreate,
    TenantShippingConfigResponse,
)
from app.services.shipping_provider_factory import build_shipping_provider, validate_credentials

logger = logging.getLogger(__name__)

FULFILLABLE_STATUS = "processing"

# Matches a trailing house/street number, e.g. "הרצל 12" -> ("הרצל", "12"),
# the same heuristic HFD's own official plugin uses to split a single
# free-text address field (see israel-shipping-sdk NOTICE / spec A.2). Only
# used as a last resort when the caller didn't send a separate house_number
# -- see _extract_recipient below for why that matters here specifically.
_TRAILING_NUMBER_RE = re.compile(r"^(.*?)\s*(\d+)\s*$")


def missing_shipping_address_fields(data: dict | None) -> list[str]:
    """Shared by checkout_service.py/marketplace_service.py (fail fast, at
    order-creation time) and _extract_recipient below (fail late, at
    fulfillment time -- the safety net for orders placed before this check
    existed, or via any client that bypasses the storefront). Only checks
    the fields that are NEVER derivable from anything else (city, phone,
    some form of street) -- house_number is deliberately not required here
    since _split_street_and_number can often recover it from a combined
    "street name + number" field."""
    data = data or {}
    missing = []
    if not data.get("city"):
        missing.append("city")
    if not (data.get("phone") or data.get("recipient_phone")):
        missing.append("phone")
    if not (data.get("street") or data.get("address_line_1") or data.get("address")):
        missing.append("street")
    return missing


async def _require_tenant_id(tenant_slug: str, db: AsyncSession) -> int:
    result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id


def _config_to_response(config: TenantShippingConfig) -> TenantShippingConfigResponse:
    return TenantShippingConfigResponse(
        id=config.id,
        provider=config.provider,
        is_active=config.is_active,
        is_default=config.is_default,
        auto_fulfill=config.auto_fulfill,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


async def list_tenant_shipping_configs_service(
    tenant_slug: str, db: AsyncSession
) -> list[TenantShippingConfigResponse]:
    tenant_id = await _require_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(TenantShippingConfig).where(TenantShippingConfig.tenant_id == tenant_id)
    )
    return [_config_to_response(c) for c in result.scalars().all()]


async def upsert_tenant_shipping_config_service(
    tenant_slug: str, req: TenantShippingConfigCreate, db: AsyncSession
) -> TenantShippingConfigResponse:
    tenant_id = await _require_tenant_id(tenant_slug, db)

    try:
        validate_credentials(req.provider, req.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = await db.execute(
        select(TenantShippingConfig).where(
            TenantShippingConfig.tenant_id == tenant_id,
            TenantShippingConfig.provider == req.provider,
        )
    )
    config = result.scalar_one_or_none()
    encrypted = encrypt_json(req.credentials)

    if req.is_default:
        # Only one default provider at a time -- clear any existing default
        # before setting this one, rather than requiring the caller to
        # unset the old one in a separate call.
        await db.execute(
            update(TenantShippingConfig)
            .where(TenantShippingConfig.tenant_id == tenant_id)
            .values(is_default=False)
        )

    if config:
        config.credentials_encrypted = encrypted
        config.sender_name = req.sender_name
        config.sender_phone = req.sender_phone
        config.sender_city = req.sender_city
        config.sender_street = req.sender_street
        config.sender_house_number = req.sender_house_number
        config.is_default = req.is_default
        config.auto_fulfill = req.auto_fulfill
        config.is_active = True
    else:
        config = TenantShippingConfig(
            tenant_id=tenant_id,
            provider=req.provider,
            credentials_encrypted=encrypted,
            sender_name=req.sender_name,
            sender_phone=req.sender_phone,
            sender_city=req.sender_city,
            sender_street=req.sender_street,
            sender_house_number=req.sender_house_number,
            is_default=req.is_default,
            auto_fulfill=req.auto_fulfill,
            is_active=True,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return _config_to_response(config)


async def delete_tenant_shipping_config_service(
    tenant_slug: str, provider: str, db: AsyncSession
) -> dict:
    tenant_id = await _require_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(TenantShippingConfig).where(
            TenantShippingConfig.tenant_id == tenant_id,
            TenantShippingConfig.provider == provider,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Shipping provider not configured")
    await db.delete(config)
    await db.commit()
    return {"status": "ok"}


async def _resolve_shipping_config(
    tenant_id: int, provider_override: str | None, db: AsyncSession, *, require_auto_fulfill: bool = False
) -> TenantShippingConfig | None:
    query = select(TenantShippingConfig).where(
        TenantShippingConfig.tenant_id == tenant_id, TenantShippingConfig.is_active == True  # noqa: E712
    )
    if require_auto_fulfill:
        query = query.where(TenantShippingConfig.auto_fulfill == True)  # noqa: E712

    if provider_override:
        result = await db.execute(query.where(TenantShippingConfig.provider == provider_override))
        return result.scalars().first()

    result = await db.execute(query)
    configs = result.scalars().all()
    for config in configs:
        if config.is_default:
            return config
    # No default set: only unambiguous if there's exactly one active config.
    return configs[0] if len(configs) == 1 else None


def _split_street_and_number(raw: str) -> tuple[str, str | None]:
    match = _TRAILING_NUMBER_RE.match(raw.strip())
    if not match:
        return raw.strip(), None
    street, number = match.groups()
    return street.strip(), number


def _extract_recipient(order: Order, customer: User) -> tuple[Contact, Address]:
    """Maps Order.shipping_json (a free-form dict -- see
    app/schemas/order_schemas.py's CheckoutRequest.shipping_address) onto
    the SDK's structured Contact/Address. Checkout now validates
    missing_shipping_address_fields itself before a physical order can even
    be created (see checkout_service.py / marketplace_service.py), so this
    is primarily a safety net for orders placed before that check existed."""
    data: dict[str, Any] = order.shipping_json or {}

    missing = missing_shipping_address_fields(data)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Order #{order.id} is missing required shipping field(s) for courier fulfillment: "
                f"{', '.join(missing)}. Checkout needs to collect these before this order can be shipped."
            ),
        )

    name = data.get("full_name") or data.get("name") or data.get("recipient_name") or customer.full_name
    phone = data.get("phone") or data.get("recipient_phone")
    city = data.get("city")
    house_number = data.get("house_number") or data.get("street_number")
    street = data.get("street")
    if not street:
        raw_address = data.get("address_line_1") or data.get("address")
        street, parsed_number = _split_street_and_number(raw_address)
        house_number = house_number or parsed_number

    if not house_number:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Order #{order.id} has a street but no recoverable house number "
                f"('{street}') -- checkout needs to collect house_number separately."
            ),
        )

    try:
        contact = Contact(name=name, phone=phone, email=data.get("email") or customer.email)
        address = Address(city=city, street=street, house_number=house_number, apartment=data.get("apartment"))
    except Exception as exc:  # pydantic ValidationError from the SDK's own models
        raise HTTPException(status_code=422, detail=f"Invalid shipping address for order #{order.id}: {exc}") from exc

    return contact, address


def _build_shipment_request(order: Order, customer: User, config: TenantShippingConfig) -> ShipmentRequest:
    recipient, recipient_address = _extract_recipient(order, customer)
    sender = Contact(name=config.sender_name, phone=config.sender_phone)
    sender_address = Address(
        city=config.sender_city, street=config.sender_street, house_number=config.sender_house_number
    )
    return ShipmentRequest(
        sender=sender,
        sender_address=sender_address,
        recipient=recipient,
        recipient_address=recipient_address,
        packages=[Package(quantity=sum(i.quantity for i in order.items) or 1)],
        order_id=order.order_number,
        notes=f"Order {order.order_number}",
    )


async def _perform_shipment(order: Order, customer: User, config: TenantShippingConfig) -> ShipmentResponse:
    """The actual courier call -- raises ShippingException on failure (or an
    HTTPException from _extract_recipient if the order's address data is
    unusable). No order mutation and no commit here, so callers with
    different error-handling needs (fulfill_order_service raises an
    HTTPException back to its caller; maybe_auto_fulfill_order below must
    never raise at all) can each decide what to do with a failure."""
    provider = build_shipping_provider(config.provider, decrypt_json(config.credentials_encrypted))
    shipment_request = _build_shipment_request(order, customer, config)
    return await provider.create_shipment(shipment_request)


def _apply_shipment_result(order: Order, config: TenantShippingConfig, shipment: ShipmentResponse) -> None:
    order.tracking_number = shipment.tracking_number
    order.shipping_label_url = shipment.label_url
    order.shipping_provider = config.provider
    order.status = "shipped"
    order.shipped_at = func.now()


async def fulfill_order_service(
    tenant_slug: str, order_id: int, db: AsyncSession, *, provider_override: str | None = None
) -> FulfillOrderResponse:
    tenant_id = await _require_tenant_id(tenant_slug, db)

    result = await db.execute(
        select(Order, User)
        .join(User, User.id == Order.user_id)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    order, customer = row

    if order.order_type != "physical":
        raise HTTPException(status_code=422, detail="Digital orders don't need a shipment")
    if order.tracking_number:
        raise HTTPException(status_code=422, detail=f"Order #{order.id} has already been fulfilled")
    if order.status != FULFILLABLE_STATUS:
        raise HTTPException(
            status_code=422,
            detail=f"Order must be '{FULFILLABLE_STATUS}' to fulfill (currently '{order.status}')",
        )

    config = await _resolve_shipping_config(tenant_id, provider_override, db)
    if not config:
        detail = (
            f"No active shipping provider '{provider_override}' configured for this store"
            if provider_override
            else "This store has no default shipping provider configured -- set one as default, "
            "or more than one is active with no default and none was specified"
        )
        raise HTTPException(status_code=422, detail=detail)

    try:
        shipment = await _perform_shipment(order, customer, config)
    except ShippingException as exc:
        raise HTTPException(
            status_code=502, detail=f"{config.provider} rejected the shipment: {exc}"
        ) from exc

    _apply_shipment_result(order, config, shipment)
    await db.commit()

    return FulfillOrderResponse(
        order_id=order.id,
        status=order.status,
        provider=config.provider,
        tracking_number=shipment.tracking_number,
        label_url=shipment.label_url,
    )


async def maybe_auto_fulfill_order(order_id: int, tenant_id: int, db: AsyncSession) -> None:
    """Called right after an order is marked 'processing' (see
    order_service.pay_order_service / mark_order_paid_by_payment_intent, and
    marketplace_service's equivalent). Deliberately never raises -- a
    courier hiccup here must not break payment confirmation, so any failure
    is logged and left for the vendor to fulfill manually via the existing
    endpoint, exactly as if auto_fulfill had never been enabled. A no-op
    for digital orders and for any tenant that hasn't opted a courier into
    auto_fulfill (the overwhelming majority, since it defaults to False)."""
    try:
        # unscoped(): this can be called from contexts with no bound tenant
        # (e.g. a global customer paying an order without a tenant_slug in
        # the URL) -- every query below already filters on the exact
        # tenant_id the order itself belongs to, so this only lifts the
        # session's "no bound tenant" guard, it doesn't widen what's read.
        with unscoped():
            result = await db.execute(
                select(Order, User)
                .join(User, User.id == Order.user_id)
                .options(selectinload(Order.items))
                .where(Order.id == order_id, Order.tenant_id == tenant_id)
            )
            row = result.first()
            if not row:
                return
            order, customer = row

            if order.order_type != "physical" or order.tracking_number:
                return

            config = await _resolve_shipping_config(tenant_id, None, db, require_auto_fulfill=True)
            if not config:
                return

            shipment = await _perform_shipment(order, customer, config)
            _apply_shipment_result(order, config, shipment)
            await db.commit()
            logger.info(
                "Auto-fulfilled order %s (tenant %s) via %s: tracking %s",
                order.id, tenant_id, config.provider, shipment.tracking_number,
            )
    except Exception:
        logger.exception(
            "Auto-fulfillment failed for order %s (tenant %s) -- left for manual fulfillment",
            order_id, tenant_id,
        )
