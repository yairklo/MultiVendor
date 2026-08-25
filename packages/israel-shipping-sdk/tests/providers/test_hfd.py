import httpx
import pytest
import respx

from israel_shipping_sdk.exceptions import ProviderAuthError, ShippingException
from israel_shipping_sdk.models import (
    Address,
    CashOnDelivery,
    Contact,
    Package,
    ShipmentRequest,
    ShipmentStatus,
)
from israel_shipping_sdk.providers.hfd import HFDProvider

BASE_URL = "https://api.hfd.co.il/rest/v2"


def _provider() -> HFDProvider:
    return HFDProvider(auth_token="test-token", client_number=12345)


def _address(**overrides) -> Address:
    defaults = {"city": "תל אביב", "street": "הרצל", "house_number": "10"}
    defaults.update(overrides)
    return Address(**defaults)


def _contact(**overrides) -> Contact:
    defaults = {"name": "דנה כהן", "phone": "0501234567"}
    defaults.update(overrides)
    return Contact(**defaults)


def _request(**overrides) -> ShipmentRequest:
    defaults = {
        "sender": _contact(name="שולח"),
        "sender_address": _address(city="חיפה"),
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
        fixture = load_fixture("hfd", "create_shipment_success.json")
        respx.post(f"{BASE_URL}/shipments/create").mock(
            return_value=httpx.Response(201, json=fixture)
        )
        response = await _provider().create_shipment(_request())
        assert response.tracking_number == "1234567"
        assert response.raw["randNumber"] == "AB12CD34"
        assert response.status == ShipmentStatus.PENDING

    @respx.mock
    async def test_create_shipment_constructs_label_url_from_shipment_number(self, load_fixture):
        fixture = load_fixture("hfd", "create_shipment_success.json")
        respx.post(f"{BASE_URL}/shipments/create").mock(
            return_value=httpx.Response(201, json=fixture)
        )
        response = await _provider().create_shipment(_request())
        assert response.label_url == f"{BASE_URL}/shipments/1234567/label"

    @respx.mock
    async def test_create_shipment_error_message_shape_raises(self, load_fixture):
        fixture = load_fixture("hfd", "create_shipment_error_message.json")
        respx.post(f"{BASE_URL}/shipments/create").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        with pytest.raises(ShippingException, match="Invalid city name"):
            await _provider().create_shipment(_request())

    @respx.mock
    async def test_create_shipment_error_details_shape_raises(self, load_fixture):
        fixture = load_fixture("hfd", "create_shipment_error_details.json")
        respx.post(f"{BASE_URL}/shipments/create").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        with pytest.raises(ShippingException, match="Missing required field"):
            await _provider().create_shipment(_request())

    @respx.mock
    async def test_create_shipment_auth_error_raises(self):
        respx.post(f"{BASE_URL}/shipments/create").mock(return_value=httpx.Response(401))
        with pytest.raises(ProviderAuthError) as excinfo:
            await _provider().create_shipment(_request())
        assert excinfo.value.provider == "hfd"


class TestPayloadMapping:
    def test_selects_locker_delivery_method_table_row(self):
        request = _request(pickup_point_id="8842")
        payload = _provider()._to_payload(request)
        assert payload["shipmentTypeCode"] == 50
        assert payload["cargoTypeHaloch"] == 11
        assert payload["cargoTypeHazor"] == 0
        assert payload["stageCode"] is None
        assert payload["pudoCodeDestination"] == 8842

    def test_selects_cod_delivery_method_table_row(self):
        request = _request(cod=CashOnDelivery(amount=150.0))
        payload = _provider()._to_payload(request)
        assert payload["shipmentTypeCode"] == 37
        assert payload["cargoTypeHaloch"] == 10
        assert payload["cargoTypeHazor"] == 100
        assert payload["productsPrice"] == 150.0
        assert payload["govina"]["sum"] == 150.0

    def test_selects_home_delivery_method_table_row(self):
        request = _request()
        payload = _provider()._to_payload(request)
        assert payload["shipmentTypeCode"] == 35
        assert payload["cargoTypeHaloch"] == 10
        assert payload["cargoTypeHazor"] == 0
        assert payload["stageCode"] == 10
        assert payload["pudoCodeDestination"] == 0

    def test_concatenates_apartment_floor_entrance_into_address_remarks(self):
        request = _request(
            recipient_address=_address(apartment="4", floor="2", entrance="B")
        )
        payload = _provider()._to_payload(request)
        assert "דירה 4" in payload["addressRemarks"]
        assert "קומה 2" in payload["addressRemarks"]
        assert "כניסה B" in payload["addressRemarks"]

    def test_address_remarks_empty_when_no_structured_fields(self):
        request = _request(recipient_address=_address())
        payload = _provider()._to_payload(request)
        assert payload["addressRemarks"] == ""


class TestCancelShipment:
    @respx.mock
    async def test_cancel_shipment_success_returns_true(self, load_fixture):
        fixture = load_fixture("hfd", "cancel_shipment_ok.json")
        respx.delete(f"{BASE_URL}/shipments/1234567").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        assert await _provider().cancel_shipment("1234567") is True

    @respx.mock
    async def test_cancel_shipment_error_raises_with_status_desc(self, load_fixture):
        fixture = load_fixture("hfd", "cancel_shipment_error.json")
        respx.delete(f"{BASE_URL}/shipments/1234567").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        with pytest.raises(ShippingException, match="Shipment already delivered"):
            await _provider().cancel_shipment("1234567")

    @respx.mock
    async def test_cancel_shipment_handles_http_error_status_before_parsing_json(self):
        respx.delete(f"{BASE_URL}/shipments/999").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(ShippingException, match="500"):
            await _provider().cancel_shipment("999")

    @respx.mock
    async def test_cancel_shipment_handles_non_json_response_body(self):
        respx.delete(f"{BASE_URL}/shipments/999").mock(
            return_value=httpx.Response(200, text="<html>not json</html>")
        )
        with pytest.raises(ShippingException, match="non-JSON"):
            await _provider().cancel_shipment("999")

    @respx.mock
    async def test_cancel_shipment_auth_error_raises_before_json_parsing(self):
        respx.delete(f"{BASE_URL}/shipments/999").mock(return_value=httpx.Response(403))
        with pytest.raises(ProviderAuthError):
            await _provider().cancel_shipment("999")


class TestPickupPoints:
    @respx.mock
    async def test_get_pickup_points_maps_spot_fields(self, load_fixture):
        fixture = load_fixture("hfd", "get_pickup_points_success.json")
        respx.post(f"{BASE_URL}/epost-points/get-list-by-address").mock(
            return_value=httpx.Response(200, json=fixture)
        )
        points = await _provider().get_pickup_points(city="תל אביב")
        assert len(points) == 2
        first = points[0]
        assert first.point_id == "8842"
        assert first.name == "כל בו שוסטר"
        assert first.house_number == "48"
        assert first.is_locker is True
        second = points[1]
        assert second.is_locker is False


class TestGetTrackingStatus:
    @respx.mock
    @pytest.mark.xfail(
        strict=False,
        reason="HFD tracking-status endpoint shape is inferred, not confirmed — see spec A.2",
    )
    async def test_get_tracking_status_unconfirmed_endpoint(self):
        respx.get(f"{BASE_URL}/shipments/1234567").mock(
            return_value=httpx.Response(200, json={"status": "IN_TRANSIT"})
        )
        result = await _provider().get_tracking_status("1234567")
        assert result.status == ShipmentStatus.IN_TRANSIT

    @respx.mock
    async def test_get_tracking_status_falls_back_to_unknown(self):
        respx.get(f"{BASE_URL}/shipments/1234567").mock(
            return_value=httpx.Response(200, json={"somethingElse": "no recognizable status"})
        )
        result = await _provider().get_tracking_status("1234567")
        assert result.status == ShipmentStatus.UNKNOWN
