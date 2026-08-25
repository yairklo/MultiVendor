from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseShippingProvider
from .models import (
    PickupPoint,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    TrackingStatusResponse,
)

if TYPE_CHECKING:
    from .address_validation import IsraelAddressValidator


class ShippingClient:
    """Thin registry so app code does
    `client.create_shipment(ProviderCode.HFD, req)` instead of importing
    provider classes directly."""

    def __init__(
        self,
        providers: dict[ProviderCode, BaseShippingProvider],
        *,
        address_validator: IsraelAddressValidator | None = None,
    ) -> None:
        self._providers = providers
        self._validator = address_validator

    def _get(self, code: ProviderCode) -> BaseShippingProvider:
        try:
            return self._providers[code]
        except KeyError:
            raise ValueError(f"No provider registered for {code}") from None

    async def create_shipment(
        self,
        provider: ProviderCode,
        request: ShipmentRequest,
        *,
        validate_address: bool = False,
    ) -> ShipmentResponse:
        if validate_address:
            if self._validator is None:
                raise ValueError("validate_address=True requires an address_validator to be configured")
            await self._validator.validate(request.recipient_address)
        return await self._get(provider).create_shipment(request)

    async def get_tracking_status(
        self, provider: ProviderCode, tracking_number: str
    ) -> TrackingStatusResponse:
        return await self._get(provider).get_tracking_status(tracking_number)

    async def get_pickup_points(
        self, provider: ProviderCode, city: str | None = None
    ) -> list[PickupPoint]:
        return await self._get(provider).get_pickup_points(city)

    async def cancel_shipment(self, provider: ProviderCode, tracking_number: str) -> bool:
        return await self._get(provider).cancel_shipment(tracking_number)
