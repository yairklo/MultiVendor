from __future__ import annotations

import httpx

from ..base import BaseShippingProvider
from ..exceptions import UnsupportedOperationError
from ..models import (
    LIONWHEEL_STATUS_MAP,
    PickupPoint,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    ShipmentStatus,
    TrackingStatusResponse,
)
from ._http import raise_for_auth_error, raise_for_not_found

_COD_TYPE_CODES = {"cash": 0, "cheque": 1, "card": 2, "bank_transfer": 3}


class LionWheelProvider(BaseShippingProvider):
    BASE_URL = "https://members.lionwheel.com/api/v1"

    def __init__(
        self,
        api_key: str,
        company_id: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._company_id = company_id
        self._client = client or httpx.AsyncClient(base_url=self.BASE_URL, timeout=15.0)

    @property
    def provider_code(self) -> ProviderCode:
        return ProviderCode.LIONWHEEL

    def _to_payload(self, request: ShipmentRequest) -> dict:
        sender_address = request.sender_address
        recipient_address = request.recipient_address

        payload: dict = {
            "original_order_id": request.order_id,
            "source_city": sender_address.city,
            "source_street": sender_address.street,
            "source_number": sender_address.house_number,
            "source_zip_code": sender_address.zip_code or "",
            "source_recipient_name": request.sender.name,
            "source_phone": request.sender.phone,
            "source_email": request.sender.email or "",
            "destination_city": recipient_address.city,
            "destination_street": recipient_address.street,
            "destination_number": recipient_address.house_number,
            "destination_zip_code": recipient_address.zip_code or "",
            "destination_apartment": recipient_address.apartment or "",
            "destination_recipient_name": request.recipient.name,
            "destination_phone": request.recipient.phone,
            "packages_quantity": sum(p.quantity for p in request.packages),
            "cod_type": 0,
        }

        if request.cod is not None:
            payload["money_collect"] = round(request.cod.amount * 100)
            payload["cod_type"] = _COD_TYPE_CODES[request.cod.cod_type.value]

        return payload

    async def create_shipment(self, request: ShipmentRequest) -> ShipmentResponse:
        resp = await self._client.post(
            "/tasks/create",
            params={"key": self._api_key},
            json={"company_id": self._company_id, **self._to_payload(request)},
        )
        raise_for_auth_error(resp, provider="lionwheel")
        resp.raise_for_status()
        body = resp.json()
        return ShipmentResponse(
            provider=ProviderCode.LIONWHEEL,
            tracking_number=str(body["task_id"]),
            label_url=body.get("label"),
            status=LIONWHEEL_STATUS_MAP.get(body.get("status", 0), ShipmentStatus.UNKNOWN),
            raw=body,
        )

    async def get_tracking_status(self, tracking_number: str) -> TrackingStatusResponse:
        resp = await self._client.get(
            f"/tasks/show/{tracking_number}", params={"key": self._api_key}
        )
        raise_for_not_found(resp, provider="lionwheel")
        raise_for_auth_error(resp, provider="lionwheel")
        resp.raise_for_status()
        body = resp.json()
        return TrackingStatusResponse(
            provider=ProviderCode.LIONWHEEL,
            tracking_number=tracking_number,
            status=LIONWHEEL_STATUS_MAP.get(body.get("status", 0), ShipmentStatus.UNKNOWN),
            raw=body,
        )

    async def cancel_shipment(self, tracking_number: str) -> bool:
        """LionWheel has no dedicated cancel endpoint (see spec A.3) —
        modeled as a status update to the CANCELED code (4)."""
        resp = await self._client.put(
            f"/tasks/{tracking_number}/update",
            params={"key": self._api_key},
            json={"status": 4},
        )
        raise_for_not_found(resp, provider="lionwheel")
        raise_for_auth_error(resp, provider="lionwheel")
        resp.raise_for_status()
        return True

    async def get_pickup_points(self, city: str | None = None) -> list[PickupPoint]:
        """No pickup-point/locker endpoint was found in LionWheel's public
        API docs (spec A.3) — LionWheel is a door-to-door last-mile
        platform. Raising here rather than fabricating an endpoint."""
        raise UnsupportedOperationError(
            "LionWheel has no documented pickup-point endpoint", provider="lionwheel"
        )
