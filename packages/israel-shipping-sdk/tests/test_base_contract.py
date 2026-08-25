import pytest

from israel_shipping_sdk.base import BaseShippingProvider
from israel_shipping_sdk.models import (
    PickupPoint,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    TrackingStatusResponse,
)
from israel_shipping_sdk.providers.hfd import HFDProvider
from israel_shipping_sdk.providers.lionwheel import LionWheelProvider


def test_base_shipping_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseShippingProvider()


class _MinimalProvider(BaseShippingProvider):
    @property
    def provider_code(self) -> ProviderCode:
        return ProviderCode.HFD

    async def create_shipment(self, request: ShipmentRequest) -> ShipmentResponse:
        raise NotImplementedError

    async def get_tracking_status(self, tracking_number: str) -> TrackingStatusResponse:
        raise NotImplementedError

    async def get_pickup_points(self, city: str | None = None) -> list[PickupPoint]:
        raise NotImplementedError

    async def cancel_shipment(self, tracking_number: str) -> bool:
        raise NotImplementedError


def test_minimal_subclass_satisfying_all_abstract_methods_can_be_instantiated():
    provider = _MinimalProvider()
    assert provider.provider_code == ProviderCode.HFD


# --- registered-provider conformance -------------------------------------
# Every concrete provider added to the SDK is listed here so the same
# interface-conformance checks run against all of them — the actual proof
# the Strategy pattern holds across one confirmed-legacy (HFD) and one
# modern-open (LionWheel) provider.

REGISTERED_PROVIDERS = [
    lambda: HFDProvider(auth_token="test-token", client_number=1),
    lambda: LionWheelProvider(api_key="test-key", company_id="co-1"),
]


@pytest.mark.parametrize("make_provider", REGISTERED_PROVIDERS)
def test_registered_provider_is_a_base_shipping_provider(make_provider):
    provider = make_provider()
    assert isinstance(provider, BaseShippingProvider)


@pytest.mark.parametrize("make_provider", REGISTERED_PROVIDERS)
def test_registered_provider_has_a_provider_code(make_provider):
    provider = make_provider()
    assert isinstance(provider.provider_code, ProviderCode)
