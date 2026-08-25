from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

_IL_LOCAL_PHONE_RE = re.compile(r"^0(5\d|[2-4]|[89]|7\d)\d{7}$")
_IL_INTL_PREFIX_RE = re.compile(r"^(?:\+972|00972|972)")


class ProviderCode(str, Enum):
    HFD = "hfd"
    LIONWHEEL = "lionwheel"


class ShipmentStatus(str, Enum):
    """Unified status. Each provider adapter maps its own codes onto this set."""

    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"
    UNKNOWN = "unknown"
    """Reserved for provider responses that don't map onto a known state —
    currently only reachable via HFD's get_tracking_status, whose response
    shape is inferred rather than confirmed (see spec Section A.2)."""


class CodType(str, Enum):
    CASH = "cash"
    CHEQUE = "cheque"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"


LIONWHEEL_STATUS_MAP: dict[int, ShipmentStatus] = {
    0: ShipmentStatus.PENDING,  # UNASSIGNED
    1: ShipmentStatus.PENDING,  # ASSIGNED
    2: ShipmentStatus.IN_TRANSIT,  # ACTIVE
    3: ShipmentStatus.DELIVERED,  # COMPLETED
    4: ShipmentStatus.CANCELLED,  # CANCELED
    5: ShipmentStatus.DELIVERED,  # ROUNDTRIP_DELIVERED
    6: ShipmentStatus.IN_TRANSIT,  # IN_INVENTORY
    7: ShipmentStatus.IN_TRANSIT,  # OUT_INVENTORY
    8: ShipmentStatus.FAILED,  # FAILED
    9: ShipmentStatus.FAILED,  # FINAL_FAILED
    10: ShipmentStatus.IN_TRANSIT,  # IN_TRANSFER
}


def normalize_il_phone(value: str) -> str:
    """Strip separators and fold +972 / 00972 / 972 international prefixes
    down to the local 0-leading form, so downstream validation only has to
    deal with one shape. Raises ValueError if the result still isn't a
    plausible Israeli number."""
    stripped = re.sub(r"[\s\-()]", "", value)
    stripped = _IL_INTL_PREFIX_RE.sub("0", stripped)
    if not _IL_LOCAL_PHONE_RE.match(stripped):
        raise ValueError(f"'{value}' is not a valid Israeli phone number")
    return stripped


class Address(BaseModel):
    city: str
    street: str
    house_number: str
    apartment: str | None = None
    entrance: str | None = None
    floor: str | None = None
    zip_code: str | None = None

    @field_validator("city", "street", "house_number")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class Contact(BaseModel):
    name: str
    phone: str
    email: EmailStr | None = None
    company: str | None = None

    @field_validator("phone")
    @classmethod
    def valid_il_phone(cls, v: str) -> str:
        return normalize_il_phone(v)


class Package(BaseModel):
    quantity: int = Field(default=1, ge=1)
    weight_kg: float | None = Field(default=None, gt=0)
    width_cm: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    length_cm: float | None = Field(default=None, gt=0)
    sku: str | None = None
    description: str | None = None


class CashOnDelivery(BaseModel):
    amount: float = Field(gt=0)
    cod_type: CodType = CodType.CASH


class ShipmentRequest(BaseModel):
    sender: Contact
    sender_address: Address
    recipient: Contact
    recipient_address: Address
    packages: list[Package] = Field(min_length=1)
    order_id: str
    notes: str | None = None
    cod: CashOnDelivery | None = None
    pickup_point_id: str | None = None
    """Set to route to a locker/pickup point instead of door delivery."""


class ShipmentResponse(BaseModel):
    provider: ProviderCode
    tracking_number: str
    label_url: str | None = None
    label_bytes: bytes | None = None
    status: ShipmentStatus
    raw: dict[str, Any]
    """Untouched provider payload — escape hatch for provider-specific fields."""


class TrackingEvent(BaseModel):
    status: ShipmentStatus
    description: str
    occurred_at: datetime | None = None


class TrackingStatusResponse(BaseModel):
    provider: ProviderCode
    tracking_number: str
    status: ShipmentStatus
    history: list[TrackingEvent] = Field(default_factory=list)
    raw: dict[str, Any]


class PickupPoint(BaseModel):
    provider: ProviderCode
    point_id: str
    name: str
    city: str
    street: str
    house_number: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_locker: bool = False
    phone: str | None = None
