import httpx
import pytest
import respx

from israel_shipping_sdk.address_validation import (
    IsraelAddressValidator,
    IsraelAddressValidatorConfig,
)
from israel_shipping_sdk.exceptions import AddressValidationError
from israel_shipping_sdk.models import Address

DATASTORE_URL = "https://data.gov.il/api/3/action/datastore_search"


def _validator(**overrides) -> IsraelAddressValidator:
    config = IsraelAddressValidatorConfig(**overrides) if overrides else IsraelAddressValidatorConfig()
    return IsraelAddressValidator(config)


def _address(city="תל אביב", street="הרצל", house_number="1") -> Address:
    return Address(city=city, street=street, house_number=house_number)


def _settlements_route(count: int = 1):
    return respx.get(DATASTORE_URL, params__contains={"resource_id": IsraelAddressValidatorConfig().settlements_resource_id}).mock(
        return_value=httpx.Response(
            200, json={"success": True, "result": {"records": [{"city_name_he": "תל אביב"}] * count}}
        )
    )


def _streets_route(count: int = 1):
    return respx.get(DATASTORE_URL, params__contains={"resource_id": IsraelAddressValidatorConfig().streets_resource_id}).mock(
        return_value=httpx.Response(
            200, json={"success": True, "result": {"records": [{"שם_רחוב": "הרצל"}] * count}}
        )
    )


class TestLiveValidation:
    @respx.mock
    async def test_validate_known_city_and_street_passes(self):
        _settlements_route(count=1)
        _streets_route(count=1)
        await _validator().validate(_address())  # no exception raised

    @respx.mock
    async def test_unknown_city_raises_address_validation_error(self):
        _settlements_route(count=0)
        with pytest.raises(AddressValidationError) as excinfo:
            await _validator().validate(_address(city="עיר שלא קיימת"))
        assert excinfo.value.field == "city"

    @respx.mock
    async def test_unknown_street_in_known_city_raises(self):
        _settlements_route(count=1)
        _streets_route(count=0)
        with pytest.raises(AddressValidationError) as excinfo:
            await _validator().validate(_address(street="רחוב שלא קיים"))
        assert excinfo.value.field == "street"

    @respx.mock
    async def test_repeat_lookup_within_ttl_hits_cache_not_network(self):
        route = _settlements_route(count=1)
        _streets_route(count=1)
        validator = _validator()
        await validator.validate(_address())
        await validator.validate(_address())
        assert route.call_count == 1


class TestGracefulFallback:
    @respx.mock
    async def test_city_validation_falls_back_to_bundled_list_on_timeout(self):
        respx.get(
            DATASTORE_URL, params__contains={"resource_id": IsraelAddressValidatorConfig().settlements_resource_id}
        ).mock(side_effect=httpx.TimeoutException("timed out"))
        _streets_route(count=1)
        # "תל אביב - יפו" is a real, bundled settlement (see data/cities.json)
        await _validator().validate(_address(city="תל אביב - יפו"))

    @respx.mock
    async def test_city_validation_falls_back_to_bundled_list_on_5xx(self):
        respx.get(
            DATASTORE_URL, params__contains={"resource_id": IsraelAddressValidatorConfig().settlements_resource_id}
        ).mock(return_value=httpx.Response(503))
        _streets_route(count=1)
        await _validator().validate(_address(city="תל אביב - יפו"))

    @respx.mock
    async def test_unknown_city_still_rejected_even_with_fallback_active(self):
        respx.get(
            DATASTORE_URL, params__contains={"resource_id": IsraelAddressValidatorConfig().settlements_resource_id}
        ).mock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(AddressValidationError) as excinfo:
            await _validator().validate(_address(city="עיר לא קיימת בכלל"))
        assert excinfo.value.field == "city"

    @respx.mock
    async def test_street_validation_fails_open_on_network_failure(self):
        # No bundled fallback exists for the streets dataset (63k+ rows,
        # too large to ship offline — see spec A.4) so a gov.il outage on
        # this specific check fails open rather than blocking checkout.
        _settlements_route(count=1)
        respx.get(
            DATASTORE_URL, params__contains={"resource_id": IsraelAddressValidatorConfig().streets_resource_id}
        ).mock(side_effect=httpx.TimeoutException("timed out"))
        await _validator().validate(_address())  # does not raise
