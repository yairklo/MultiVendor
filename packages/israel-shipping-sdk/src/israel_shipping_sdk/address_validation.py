"""Gov.il (data.gov.il) address validation.

Resource ids below were resolved and verified live (not guessed) while
building this SDK — see spec Section A.4 for the research trail:

- settlements: https://data.gov.il/dataset/citiesandsettelments,
  resource_id=8f714b6f-c35c-4b40-a0e7-547b675eee0e, confirmed returning
  1,310 real records with fields city_code/city_name_he/city_name_en.
- streets: https://data.gov.il/dataset/321,
  resource_id=9ad3862c-8391-4b2f-84a4-2d4c68625f4b, confirmed returning
  63,571 real records with fields סמל_ישוב/שם_ישוב/סמל_רחוב/שם_רחוב.

CKAN resource ids for "מתעדכן" (actively-updated) datasets are not
guaranteed permanently stable across republishes. If data.gov.il ever
rotates these, override the config fields rather than editing this file in
place — a stale id fails loudly (empty result sets, meaning every address
looks unknown) rather than silently.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from importlib import resources

import httpx

from .exceptions import AddressValidationError
from .models import Address

_FALLBACK_CITIES_CACHE: list[dict] | None = None


def _load_fallback_cities() -> list[dict]:
    """The settlements list (~1,300 rows) is small enough to bundle offline
    (src/israel_shipping_sdk/data/cities.json, fetched live from the
    resource above) so city validation survives a data.gov.il outage. The
    streets dataset (63k+ rows) is not — see _validate_street's fail-open
    handling instead."""
    global _FALLBACK_CITIES_CACHE
    if _FALLBACK_CITIES_CACHE is None:
        data_path = resources.files("israel_shipping_sdk").joinpath("data").joinpath("cities.json")
        with data_path.open(encoding="utf-8") as f:
            payload = json.load(f)
        _FALLBACK_CITIES_CACHE = payload["cities"]
    return _FALLBACK_CITIES_CACHE


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("-", " ")).strip().casefold()


@dataclass
class IsraelAddressValidatorConfig:
    settlements_resource_id: str = "8f714b6f-c35c-4b40-a0e7-547b675eee0e"
    streets_resource_id: str = "9ad3862c-8391-4b2f-84a4-2d4c68625f4b"
    base_url: str = "https://data.gov.il/api/3/action/datastore_search"
    cache_ttl_seconds: int = 86_400
    request_timeout_seconds: float = 5.0


class IsraelAddressValidator:
    def __init__(
        self,
        config: IsraelAddressValidatorConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or IsraelAddressValidatorConfig()
        self._client = client or httpx.AsyncClient(timeout=self._config.request_timeout_seconds)
        self._city_cache: dict[str, tuple[bool, float]] = {}

    async def validate(self, address: Address) -> None:
        await self._validate_city(address.city)
        await self._validate_street(address.city, address.street)

    async def _validate_city(self, city: str) -> None:
        normalized = _normalize(city)
        cached = self._city_cache.get(normalized)
        if cached is not None and time.monotonic() < cached[1]:
            found = cached[0]
        else:
            found = await self._city_exists(city, normalized)
            self._city_cache[normalized] = (found, time.monotonic() + self._config.cache_ttl_seconds)

        if not found:
            raise AddressValidationError(f"Unknown city: {city!r}", field="city")

    async def _city_exists(self, city: str, normalized: str) -> bool:
        try:
            resp = await self._client.get(
                self._config.base_url,
                params={
                    "resource_id": self._config.settlements_resource_id,
                    "q": city,
                    "limit": 5,
                },
            )
        except httpx.TimeoutException:
            return self._city_in_bundled_fallback(normalized)

        if resp.status_code >= 500:
            return self._city_in_bundled_fallback(normalized)

        records = resp.json().get("result", {}).get("records", [])
        return len(records) > 0

    def _city_in_bundled_fallback(self, normalized: str) -> bool:
        return any(
            _normalize(c["city_name_he"]) == normalized or _normalize(c["city_name_en"]) == normalized
            for c in _load_fallback_cities()
        )

    async def _validate_street(self, city: str, street: str) -> None:
        # Deliberately not cached, unlike _validate_city: the fail-open
        # result below would otherwise get pinned for cache_ttl_seconds
        # (up to 24h) even after data.gov.il recovers, silently suppressing
        # real street validation for that whole window. Caching only
        # helps the network-call-avoidance case, which isn't worth that
        # risk for a check that already degrades gracefully on failure.
        try:
            resp = await self._client.get(
                self._config.base_url,
                params={
                    "resource_id": self._config.streets_resource_id,
                    "q": street,
                    "limit": 5,
                },
            )
        except httpx.TimeoutException:
            return  # fail open — no bundled fallback for 63k+ street rows

        if resp.status_code >= 500:
            return  # fail open, same reasoning

        records = resp.json().get("result", {}).get("records", [])
        if not records:
            raise AddressValidationError(
                f"Unknown street {street!r} in {city!r}", field="street"
            )
