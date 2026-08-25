# israel-shipping-sdk

A unified, async Python SDK for Israeli courier APIs. One `ShipmentRequest`
model in, a normalized `ShipmentResponse` out — regardless of which courier
is behind it.

## Why this exists

Israeli courier integration is fragmented: some couriers publish clean
REST docs, some publish nothing at all and are only reachable by reading
their own WooCommerce/Shopify plugin source. This SDK does that research
once and ships a typed, tested client so application code doesn't have to.

| Provider | Protocol | Public docs | Notes |
|---|---|---|---|
| **HFD** | REST / JSON | None — reverse-engineered from HFD's own official `hfd-epost-integration` WooCommerce plugin (GPLv2, v2.21). See `NOTICE`. | Needs an `auth_token` + `client_number` from HFD directly — that part was never public and this SDK doesn't change it. |
| **LionWheel** | REST / JSON | Yes — [github.com/lionwheel/api](https://github.com/lionwheel/api) | Self-serve API key. No pickup-point endpoint is documented, so `get_pickup_points()` raises `UnsupportedOperationError`. |

A third provider, CARGO, was researched (genuine self-serve OpenAPI docs)
but deferred past `v0.1.0` to keep the initial release to two providers —
see the technical spec's Appendix A.6 for everything needed to add it
following the same pattern as LionWheel.

## Install

```bash
pip install israel-shipping-sdk
```

## Quickstart

```python
import asyncio
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


async def main():
    client = ShippingClient({
        ProviderCode.HFD: HFDProvider(auth_token="...", client_number=12345),
        ProviderCode.LIONWHEEL: LionWheelProvider(api_key="...", company_id="..."),
    })

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
    print(response.tracking_number, response.label_url)


asyncio.run(main())
```

### Optional: validating addresses before you ship

```python
from israel_shipping_sdk.address_validation import IsraelAddressValidator

validator = IsraelAddressValidator()  # ships with verified, real data.gov.il resource ids
client = ShippingClient({...}, address_validator=validator)

response = await client.create_shipment(ProviderCode.HFD, request, validate_address=True)
```

City validation checks live against `data.gov.il` and falls back to a
bundled snapshot of all 1,310 Israeli settlements if the government API is
slow or down. Street validation (63,000+ rows — too large to bundle) checks
live only, and fails open (doesn't block the shipment) if `data.gov.il` is
unreachable.

## Adding a new provider

Implement `BaseShippingProvider` (`src/israel_shipping_sdk/base.py`) and
make sure it passes the shared conformance suite in
`tests/test_base_contract.py` — every registered provider runs through the
same interface tests, which is what keeps the Strategy pattern honest as
providers are added.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
mypy src/
```

See `CONTRIBUTING.md` for the TDD workflow this project follows, and
`NOTICE` for where the HFD provider's protocol documentation came from.
