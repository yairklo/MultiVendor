import pytest
from pydantic import ValidationError

from israel_shipping_sdk.models import (
    Address,
    CashOnDelivery,
    Contact,
    Package,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    ShipmentStatus,
    TrackingStatusResponse,
)


class TestAddress:
    def test_rejects_blank_city(self):
        with pytest.raises(ValidationError):
            Address(city="   ", street="Herzl", house_number="1")

    def test_rejects_blank_street(self):
        with pytest.raises(ValidationError):
            Address(city="Tel Aviv", street="", house_number="1")

    def test_rejects_blank_house_number(self):
        with pytest.raises(ValidationError):
            Address(city="Tel Aviv", street="Herzl", house_number=" ")

    def test_strips_whitespace(self):
        addr = Address(city=" Tel Aviv ", street=" Herzl ", house_number=" 1 ")
        assert addr.city == "Tel Aviv"
        assert addr.street == "Herzl"
        assert addr.house_number == "1"


class TestContactPhone:
    @pytest.mark.parametrize("bad", ["12345", "abcdefghij", "", "0"])
    def test_rejects_invalid_phone(self, bad):
        with pytest.raises(ValidationError):
            Contact(name="Dana", phone=bad)

    @pytest.mark.parametrize("good", ["050-1234567", "0501234567", "02-1234567"])
    def test_accepts_valid_local_phone(self, good):
        contact = Contact(name="Dana", phone=good)
        assert contact.phone.startswith("0")

    @pytest.mark.parametrize(
        "intl,expected_local",
        [
            ("+972501234567", "0501234567"),
            ("00972501234567", "0501234567"),
            ("972501234567", "0501234567"),
            ("+972-50-123-4567", "0501234567"),
        ],
    )
    def test_normalizes_international_prefix_to_local(self, intl, expected_local):
        contact = Contact(name="Dana", phone=intl)
        assert contact.phone == expected_local


class TestPackage:
    def test_default_quantity_is_one(self):
        assert Package().quantity == 1

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            Package(quantity=0)

    def test_rejects_non_positive_weight(self):
        with pytest.raises(ValidationError):
            Package(weight_kg=0)


class TestShipmentRequest:
    def _address(self):
        return Address(city="Tel Aviv", street="Herzl", house_number="1")

    def _contact(self):
        return Contact(name="Dana", phone="0501234567")

    def test_rejects_empty_packages_list(self):
        with pytest.raises(ValidationError):
            ShipmentRequest(
                sender=self._contact(),
                sender_address=self._address(),
                recipient=self._contact(),
                recipient_address=self._address(),
                packages=[],
                order_id="ORD-1",
            )

    def test_accepts_minimal_valid_request(self):
        req = ShipmentRequest(
            sender=self._contact(),
            sender_address=self._address(),
            recipient=self._contact(),
            recipient_address=self._address(),
            packages=[Package()],
            order_id="ORD-1",
        )
        assert req.order_id == "ORD-1"
        assert req.cod is None
        assert req.pickup_point_id is None


class TestRoundTrip:
    def test_shipment_response_round_trips(self):
        resp = ShipmentResponse(
            provider=ProviderCode.HFD,
            tracking_number="123",
            status=ShipmentStatus.PENDING,
            raw={"shipmentNumber": "123"},
        )
        dumped = resp.model_dump()
        restored = ShipmentResponse.model_validate(dumped)
        assert restored == resp

    def test_tracking_status_response_round_trips_with_unknown_status(self):
        resp = TrackingStatusResponse(
            provider=ProviderCode.HFD,
            tracking_number="123",
            status=ShipmentStatus.UNKNOWN,
            raw={},
        )
        dumped = resp.model_dump()
        restored = TrackingStatusResponse.model_validate(dumped)
        assert restored.status == ShipmentStatus.UNKNOWN

    def test_cash_on_delivery_requires_positive_amount(self):
        with pytest.raises(ValidationError):
            CashOnDelivery(amount=0)
