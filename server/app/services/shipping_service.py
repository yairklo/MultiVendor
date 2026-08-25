import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from israel_shipping_sdk.exceptions import ShippingException
from israel_shipping_sdk.models import Address, Contact, Package, ShipmentRequest

from app.core.crypto import decrypt_json, encrypt_json
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

FULFILLABLE_STATUS = "processing"

# Matches a trailing house/street number, e.g. "הרצל 12" -> ("הרצל", "12"),
# the same heuristic HFD's own official plugin uses to split a single
# free-text address field (see israel-shipping-sdk NOTICE / spec A.2). Only
# used as a last resort when the caller didn't send a separate house_number
# -- see _extract_recipient below for why that matters here specifically.
_TRAILING_NUMBER_RE = re.compile(r"^(.*?)\s*(\d+)\s*$")


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
    tenant_id: int, provider_override: str | None, db: AsyncSession
) -> TenantShippingConfig | None:
    query = select(TenantShippingConfig).where(
        TenantShippingConfig.tenant_id == tenant_id, TenantShippingConfig.is_active == True  # noqa: E712
    )
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
    the SDK's structured Contact/Address. This is deliberately defensive,
    not a silent best-effort guess: as of this writing, checkout
    (frontend/src/app/checkout/page.tsx) only ever sends
    {full_name, email, address_line_1} -- no city, no phone, no house
    number -- so most real orders will hit the missing-fields error below
    until checkout is extended to collect them. That gap is called out
    in the shipping integration's own docs; this function's job is only to
    fail with a clear, itemized message when it happens, not to paper over
    it with a fabricated city or phone number."""
    data: dict[str, Any] = order.shipping_json or {}

    name = data.get("full_name") or data.get("name") or data.get("recipient_name") or customer.full_name
    phone = data.get("phone") or data.get("recipient_phone")
    city = data.get("city")
    house_number = data.get("house_number") or data.get("street_number")
    street = data.get("street")
    if not street:
        raw_address = data.get("address_line_1") or data.get("address")
        if raw_address:
            street, parsed_number = _split_street_and_number(raw_address)
            house_number = house_number or parsed_number

    missing = [
        field
        for field, value in (("city", city), ("street", street), ("house_number", house_number), ("phone", phone))
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Order #{order.id} is missing required shipping field(s) for courier fulfillment: "
                f"{', '.join(missing)}. Checkout needs to collect these before this order can be shipped."
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

    provider = build_shipping_provider(config.provider, decrypt_json(config.credentials_encrypted))
    shipment_request = _build_shipment_request(order, customer, config)

    try:
        result = await provider.create_shipment(shipment_request)
    except ShippingException as exc:
        raise HTTPException(
            status_code=502, detail=f"{config.provider} rejected the shipment: {exc}"
        ) from exc

    order.tracking_number = result.tracking_number
    order.shipping_label_url = result.label_url
    order.shipping_provider = config.provider
    order.status = "shipped"
    order.shipped_at = func.now()
    await db.commit()

    return FulfillOrderResponse(
        order_id=order.id,
        status=order.status,
        provider=config.provider,
        tracking_number=result.tracking_number,
        label_url=result.label_url,
    )
