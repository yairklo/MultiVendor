import pytest

from israel_shipping_sdk.client import ShippingClient
from israel_shipping_sdk.exceptions import AddressValidationError
from israel_shipping_sdk.models import (
    Address,
    Contact,
    Package,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    ShipmentStatus,
)


class _FakeProvider:
    def __init__(self):
        self.create_calls = []

    @property
    def provider_code(self):
        return ProviderCode.HFD

    async def create_shipment(self, request):
        self.create_calls.append(request)
        return ShipmentResponse(
            provider=ProviderCode.HFD, tracking_number="1", status=ShipmentStatus.PENDING, raw={}
        )

    async def get_tracking_status(self, tracking_number):
        raise NotImplementedError

    async def get_pickup_points(self, city=None):
        raise NotImplementedError

    async def cancel_shipment(self, tracking_number):
        raise NotImplementedError


class _FakeValidator:
    def __init__(self, should_raise: bool = False):
        self.validated = []
        self._should_raise = should_raise

    async def validate(self, address):
        self.validated.append(address)
        if self._should_raise:
            raise AddressValidationError("bad address", field="city")


def _request() -> ShipmentRequest:
    address = Address(city="Tel Aviv", street="Herzl", house_number="1")
    contact = Contact(name="Dana", phone="0501234567")
    return ShipmentRequest(
        sender=contact,
        sender_address=address,
        recipient=contact,
        recipient_address=address,
        packages=[Package()],
        order_id="ORD-1",
    )


class TestShippingClient:
    async def test_create_shipment_dispatches_to_registered_provider(self):
        provider = _FakeProvider()
        client = ShippingClient({ProviderCode.HFD: provider})
        response = await client.create_shipment(ProviderCode.HFD, _request())
        assert response.tracking_number == "1"
        assert len(provider.create_calls) == 1

    async def test_unregistered_provider_raises_value_error(self):
        client = ShippingClient({})
        with pytest.raises(ValueError):
            await client.create_shipment(ProviderCode.HFD, _request())

    async def test_validate_address_true_calls_validator_before_provider(self):
        provider = _FakeProvider()
        validator = _FakeValidator()
        client = ShippingClient({ProviderCode.HFD: provider}, address_validator=validator)
        await client.create_shipment(ProviderCode.HFD, _request(), validate_address=True)
        assert len(validator.validated) == 1
        assert len(provider.create_calls) == 1

    async def test_validation_failure_prevents_provider_call(self):
        provider = _FakeProvider()
        validator = _FakeValidator(should_raise=True)
        client = ShippingClient({ProviderCode.HFD: provider}, address_validator=validator)
        with pytest.raises(AddressValidationError):
            await client.create_shipment(ProviderCode.HFD, _request(), validate_address=True)
        assert len(provider.create_calls) == 0

    async def test_validate_address_true_without_validator_configured_raises(self):
        provider = _FakeProvider()
        client = ShippingClient({ProviderCode.HFD: provider})
        with pytest.raises(ValueError):
            await client.create_shipment(ProviderCode.HFD, _request(), validate_address=True)
