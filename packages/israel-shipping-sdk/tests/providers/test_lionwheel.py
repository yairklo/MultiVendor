import httpx
import pytest
import respx

from israel_shipping_sdk.exceptions import (
    ProviderAuthError,
    ShipmentNotFoundError,
    UnsupportedOperationError,
)
from israel_shipping_sdk.models import (
    LIONWHEEL_STATUS_MAP,
    Address,
    Contact,
    Package,
    ShipmentRequest,
    ShipmentStatus,
)
from israel_shipping_sdk.providers.lionwheel import LionWheelProvider

BASE_URL = "https://members.lionwheel.com/api/v1"


def _provider() -> LionWheelProvider:
    return LionWheelProvider(api_key="test-key", company_id="co-1")


def _address(**overrides) -> Address:
    defaults = {"city": "Tel Aviv", "street": "Herzl", "house_number": "10"}
    defaults.update(overrides)
    return Address(**defaults)


def _contact(**overrides) -> Contact:
    defaults = {"name": "Dana Cohen", "phone": "0501234567"}
    defaults.update(overrides)
    return Contact(**defaults)


def _request(**overrides) -> ShipmentRequest:
    defaults = {
        "sender": _contact(name="Sender"),
        "sender_address": _address(city="Haifa"),
        "recipient": _contact(),
        "recipient_address": _address(),
        "packages": [Package()],
        "order_id": "ORD-1",
    }
    defaults.update(overrides)
    return ShipmentRequest(**defaults)


class TestCreateShipment:
    @respx.mock
    async def test_create_shipment_success(self, load_fixture):
        fixture = load_fixture("lionwheel", "create_shipment_success.json")
        respx.post(f"{BASE_URL}/tasks/create").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        response = await _provider().create_shipment(_request())
        assert response.tracking_number == "918273"
        assert response.label_url == "https://members.lionwheel.com/labels/918273.pdf"
        assert response.status == ShipmentStatus.PENDING
        assert response.raw["public_id"] == "LW-918273"

    @respx.mock
    async def test_create_shipment_sends_key_as_query_param_and_company_id_in_body(
        self, load_fixture
    ):
        fixture = load_fixture("lionwheel", "create_shipment_success.json")
        route = respx.post(f"{BASE_URL}/tasks/create").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        await _provider().create_shipment(_request())
        request = route.calls.last.request
        assert request.url.params["key"] == "test-key"

    @respx.mock
    async def test_create_shipment_auth_error_raises(self, load_fixture):
        fixture = load_fixture("lionwheel", "create_shipment_auth_error.json")
        respx.post(f"{BASE_URL}/tasks/create").mock(
            return_value=httpx.Response(401, json=fixture)
        )
        with pytest.raises(ProviderAuthError) as excinfo:
            await _provider().create_shipment(_request())
        assert excinfo.value.provider == "lionwheel"


class TestPayloadMapping:
    def test_flattens_addresses_into_source_and_destination_fields(self):
        request = _request()
        payload = _provider()._to_payload(request)
        assert payload["destination_city"] == "Tel Aviv"
        assert payload["destination_street"] == "Herzl"
        assert payload["destination_number"] == "10"
        assert payload["destination_recipient_name"] == "Dana Cohen"
        assert payload["destination_phone"] == "0501234567"
        assert payload["source_city"] == "Haifa"
        assert payload["source_recipient_name"] == "Sender"
        assert payload["packages_quantity"] == 1

    def test_cod_maps_to_money_collect_in_agorot(self):
        from israel_shipping_sdk.models import CashOnDelivery

        request = _request(cod=CashOnDelivery(amount=25.5))
        payload = _provider()._to_payload(request)
        assert payload["money_collect"] == 2550
        assert payload["cod_type"] == 0


class TestGetTrackingStatus:
    @respx.mock
    async def test_maps_all_known_status_codes(self, load_fixture):
        fixture = load_fixture("lionwheel", "get_status_success.json")
        for code, expected in LIONWHEEL_STATUS_MAP.items():
            fixture = {**fixture, "status": code}
            respx.get(f"{BASE_URL}/tasks/show/918273").mock(
                return_value=httpx.Response(200, json=fixture)
            )
            result = await _provider().get_tracking_status("918273")
            assert result.status == expected, f"status code {code} mismapped"

    @respx.mock
    async def test_not_found_raises(self, load_fixture):
        fixture = load_fixture("lionwheel", "get_status_not_found.json")
        respx.get(f"{BASE_URL}/tasks/show/999").mock(
            return_value=httpx.Response(404, json=fixture)
        )
        with pytest.raises(ShipmentNotFoundError):
            await _provider().get_tracking_status("999")


class TestCancelShipment:
    @respx.mock
    async def test_cancel_shipment_uses_update_endpoint_with_canceled_status(self):
        route = respx.put(f"{BASE_URL}/tasks/918273/update").mock(
            return_value=httpx.Response(200, json={"task_id": 918273, "status": 4})
        )
        result = await _provider().cancel_shipment("918273")
        assert result is True
        sent_body = route.calls.last.request.content
        assert b'"status": 4' in sent_body or b'"status":4' in sent_body

    @respx.mock
    async def test_cancel_shipment_not_found_raises(self):
        respx.put(f"{BASE_URL}/tasks/999/update").mock(return_value=httpx.Response(404))
        with pytest.raises(ShipmentNotFoundError):
            await _provider().cancel_shipment("999")


class TestPickupPoints:
    async def test_get_pickup_points_is_unsupported(self):
        # A.3's research (github.com/lionwheel/api) never surfaced a
        # pickup-point/locker endpoint — LionWheel is a door-to-door last
        # mile platform. Rather than fabricate an endpoint, this is
        # explicitly unsupported.
        with pytest.raises(UnsupportedOperationError):
            await _provider().get_pickup_points()
