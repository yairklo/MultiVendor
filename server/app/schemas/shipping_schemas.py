from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict


ShippingProviderCode = Literal["hfd", "lionwheel"]


class TenantShippingConfigCreate(BaseModel):
    provider: ShippingProviderCode
    # Shape depends on provider: {"auth_token": str, "client_number": int}
    # for hfd, {"api_key": str, "company_id": str} for lionwheel -- validated
    # against the provider's actual required keys in shipping_service before
    # being encrypted, not here (this schema only knows it's "some dict").
    credentials: Dict[str, Any]
    # The pickup address this courier account collects from -- required
    # because there is nowhere else in the schema with a store phone/address
    # (see app/models/shipping_config.py).
    sender_name: str
    sender_phone: str
    sender_city: str
    sender_street: str
    sender_house_number: str
    is_default: bool = False
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "provider": "hfd",
            "credentials": {"auth_token": "xxxxx", "client_number": 12345},
            "sender_name": "My Store LTD",
            "sender_phone": "03-1234567",
            "sender_city": "תל אביב",
            "sender_street": "הרצל",
            "sender_house_number": "1",
            "is_default": True,
        }
    })


class TenantShippingConfigResponse(BaseModel):
    # Deliberately has no credentials field -- decrypting for display would
    # mean the plaintext token crosses the wire again for no reason. If a
    # vendor needs to check what's configured, they re-enter it.
    id: int
    provider: ShippingProviderCode
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class FulfillOrderRequest(BaseModel):
    # None (the default) means "use the tenant's default active config" --
    # only needed when a vendor has more than one courier connected and
    # wants to override which one ships this particular order.
    provider: Optional[ShippingProviderCode] = None


class FulfillOrderResponse(BaseModel):
    order_id: int
    status: str
    provider: ShippingProviderCode
    tracking_number: str
    label_url: Optional[str] = None
