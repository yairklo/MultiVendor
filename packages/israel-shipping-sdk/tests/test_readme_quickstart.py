"""Not part of the TDD provider suites — this exercises the exact import
and construction shape shown in README.md's quickstart, so the README
can't silently drift from what the package actually exports."""
import httpx
import respx

from israel_shipping_sdk import (
    Address,
    CashOnDelivery,
    Contact,
    Package,
    ProviderCode,
    ShipmentRequest,
    ShippingClient,
)
from israel_shipping_sdk.providers.hfd import HFDProvider
from israel_shipping_sdk.providers.lionwheel import LionWheelProvider


@respx.mock
async def test_readme_quickstart_shape_works_end_to_end():
    respx.post("https://api.hfd.co.il/rest/v2/shipments/create").mock(
        return_value=httpx.Response(200, json={"shipmentNumber": "1234567", "randNumber": "AB12CD34"})
    )

    client = ShippingClient(
        {
            ProviderCode.HFD: HFDProvider(auth_token="...", client_number=12345),
            ProviderCode.LIONWHEEL: LionWheelProvider(api_key="...", company_id="..."),
        }
    )

    request = ShipmentRequest(
        sender=Contact(name="Store LTD", phone="03-1234567"),
        sender_address=Address(city="תל אביב", street="הרצל", house_number="1"),
        recipient=Contact(name="דנה כהן", phone="050-1234567"),
        recipient_address=Address(city="חיפה", street="הנביאים", house_number="22", apartment="4"),
        packages=[Package(weight_kg=1.2)],
        order_id="ORD-1001",
        cod=CashOnDelivery(amount=150.0),
    )

    response = await client.create_shipment(ProviderCode.HFD, request)
    assert response.tracking_number == "1234567"
    assert response.label_url == "https://api.hfd.co.il/rest/v2/shipments/1234567/label"
