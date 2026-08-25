from abc import ABC, abstractmethod

from .models import (
    PickupPoint,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    TrackingStatusResponse,
)


class BaseShippingProvider(ABC):
    """Every provider adapter implements this. The client never talks to
    a provider's raw HTTP surface directly — it only ever calls through
    here, so swapping or adding a courier never touches call sites."""

    @property
    @abstractmethod
    def provider_code(self) -> ProviderCode: ...

    @abstractmethod
    async def create_shipment(self, request: ShipmentRequest) -> ShipmentResponse: ...

    @abstractmethod
    async def get_tracking_status(self, tracking_number: str) -> TrackingStatusResponse: ...

    @abstractmethod
    async def get_pickup_points(self, city: str | None = None) -> list[PickupPoint]: ...

    @abstractmethod
    async def cancel_shipment(self, tracking_number: str) -> bool:
        """Return True if cancelled, False is never used silently — a
        provider explicitly reporting failure (e.g. HFD's
        {"status": "ERROR", "status_desc": ...}) should raise
        ShippingException carrying that description, so callers know *why*
        rather than just getting a falsy result. Raise
        UnsupportedOperationError only when a provider has no cancellation
        path at all — HFD has a confirmed dedicated DELETE endpoint;
        LionWheel does not and is modeled as a status-update call instead."""
        ...
