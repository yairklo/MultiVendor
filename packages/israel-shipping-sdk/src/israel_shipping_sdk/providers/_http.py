"""Shared HTTP error-mapping helpers. Extracted once both HFD and LionWheel
adapters needed the same translation from raw status codes to SDK
exceptions, rather than built speculatively ahead of that duplication being
real. Kept as two small independent checks (rather than one combined
helper) because not every call site wants both — a create-shipment call has
no sensible reading of a 404, for instance."""
from __future__ import annotations

import httpx

from ..exceptions import ProviderAuthError, ShipmentNotFoundError


def raise_for_auth_error(resp: httpx.Response, *, provider: str) -> None:
    if resp.status_code in (401, 403):
        raise ProviderAuthError(
            f"{provider} rejected the credentials", provider=provider, status_code=resp.status_code
        )


def raise_for_not_found(resp: httpx.Response, *, provider: str) -> None:
    if resp.status_code == 404:
        raise ShipmentNotFoundError(
            f"{provider} could not find that shipment", provider=provider, status_code=resp.status_code
        )
