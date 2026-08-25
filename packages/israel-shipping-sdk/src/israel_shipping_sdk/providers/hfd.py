# Source: wire protocol reverse-engineered from HFD's own official
# WooCommerce plugin, `hfd-epost-integration` v2.21 (GPLv2, published by
# HFD on wordpress.org). Endpoint URLs, field names, and status codes below
# are interoperability facts read out of that plugin's PHP source — no code
# from the plugin was copied or adapted; this module is an independent
# implementation of the documented wire shapes. See spec Section A.2 for
# the full research trail, including which behaviors (get_tracking_status)
# were never observed being called and are therefore inferred, not
# confirmed.
from __future__ import annotations

import json as _json

import httpx

from ..base import BaseShippingProvider
from ..exceptions import ShippingException
from ..models import (
    Address,
    PickupPoint,
    ProviderCode,
    ShipmentRequest,
    ShipmentResponse,
    ShipmentStatus,
    TrackingStatusResponse,
)
from ._http import raise_for_auth_error

_HFD_STATUS_FIELD_MAP: dict[str, ShipmentStatus] = {
    "PENDING": ShipmentStatus.PENDING,
    "IN_TRANSIT": ShipmentStatus.IN_TRANSIT,
    "DELIVERED": ShipmentStatus.DELIVERED,
    "CANCELLED": ShipmentStatus.CANCELLED,
    "FAILED": ShipmentStatus.FAILED,
}


class HFDProvider(BaseShippingProvider):
    BASE_URL = "https://api.hfd.co.il/rest/v2"

    def __init__(
        self,
        auth_token: str,
        client_number: int,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_number = client_number
        self._client = client or httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=15.0,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    @property
    def provider_code(self) -> ProviderCode:
        return ProviderCode.HFD

    @staticmethod
    def _address_remarks(address: Address) -> str:
        """HFD's own plugin sends free-text remarks; it never structures
        apartment/floor/entrance into their own fields, so this SDK folds
        them into addressRemarks using the plugin's own Hebrew labels
        (דירה/קומה/כניסה) rather than dropping them."""
        parts: list[str] = []
        if address.apartment:
            parts.append(f"דירה {address.apartment}")
        if address.floor:
            parts.append(f"קומה {address.floor}")
        if address.entrance:
            parts.append(f"כניסה {address.entrance}")
        return " ".join(parts)

    def _to_payload(self, request: ShipmentRequest) -> dict:
        recipient_address = request.recipient_address

        if request.pickup_point_id is not None:
            shipment_type_code, cargo_type_haloch, cargo_type_hazor = 50, 11, 0
            stage_code: int | None = None
            pudo_code_destination = int(request.pickup_point_id)
        elif request.cod is not None:
            shipment_type_code, cargo_type_haloch, cargo_type_hazor = 37, 10, 100
            stage_code = None
            pudo_code_destination = 0
        else:
            shipment_type_code, cargo_type_haloch, cargo_type_hazor = 35, 10, 0
            stage_code = 10
            pudo_code_destination = 0

        payload: dict = {
            "mesiraIsuf": "מסירה",
            "shipmentTypeCode": shipment_type_code,
            "cargoTypeHaloch": cargo_type_haloch,
            "cargoTypeHazor": cargo_type_hazor,
            "addressRemarks": self._address_remarks(recipient_address),
            "shipmentRemarks": request.notes or "",
            "stageCode": stage_code,
            "pudoCodeDestination": pudo_code_destination,
            "ordererName": request.sender.name,
            "houseNum": recipient_address.house_number,
            "apartment": recipient_address.apartment or "",
            "floor": recipient_address.floor or "",
            "entrance": recipient_address.entrance or "",
            "nameTo": request.recipient.name,
            "streetName": recipient_address.street,
            "cityName": recipient_address.city,
            "telFirst": request.recipient.phone,
            "streetCode": "",
            "referenceNum1": request.order_id,
            "email": request.recipient.email or "",
            "productsPrice": 0.0,
            "packsHaloch": str(sum(p.quantity for p in request.packages)),
        }

        if request.cod is not None:
            payload["productsPrice"] = request.cod.amount
            payload["govina"] = {"code": 1, "sum": request.cod.amount}

        return payload

    async def create_shipment(self, request: ShipmentRequest) -> ShipmentResponse:
        resp = await self._client.post(
            "/shipments/create",
            json={"clientNumber": self._client_number, **self._to_payload(request)},
        )
        raise_for_auth_error(resp, provider="hfd")
        body = resp.json()
        if "shipmentNumber" not in body or not body["shipmentNumber"]:
            message = body.get("errorMessage") or body.get("details") or "Unknown HFD error"
            raise ShippingException(message, provider="hfd", status_code=resp.status_code, raw=body)

        shipment_number = body["shipmentNumber"]
        return ShipmentResponse(
            provider=ProviderCode.HFD,
            tracking_number=shipment_number,
            label_url=f"{self.BASE_URL}/shipments/{shipment_number}/label",
            status=ShipmentStatus.PENDING,
            raw=body,
        )

    async def cancel_shipment(self, tracking_number: str) -> bool:
        resp = await self._client.request("DELETE", f"/shipments/{tracking_number}")

        raise_for_auth_error(resp, provider="hfd")
        if resp.status_code >= 400:
            raise ShippingException(
                f"HFD cancellation request failed with HTTP {resp.status_code}",
                provider="hfd",
                status_code=resp.status_code,
                raw=resp.text,
            )

        try:
            body = resp.json()
        except (_json.JSONDecodeError, ValueError) as exc:
            raise ShippingException(
                "HFD returned a non-JSON response to the cancellation request",
                provider="hfd",
                status_code=resp.status_code,
                raw=resp.text,
            ) from exc

        if body.get("status") == "OK":
            return True
        raise ShippingException(
            body.get("status_desc", "HFD cancellation failed"), provider="hfd", raw=body
        )

    async def get_pickup_points(self, city: str | None = None) -> list[PickupPoint]:
        resp = await self._client.post(
            "/epost-points/get-list-by-address",
            json={
                "clientId": str(self._client_number),
                "city": city or "",
                "shipmentDirection": "מסירה",
                "language": "HE",
                "street": "",
                "openingHoursFormat": False,
            },
        )
        spots = resp.json()
        return [
            PickupPoint(
                provider=ProviderCode.HFD,
                point_id=str(spot.get("spotId", "")),
                name=spot.get("spotName", ""),
                city=spot.get("city", ""),
                street=spot.get("street", ""),
                house_number=spot.get("houseNo") or None,
                latitude=spot.get("latitude"),
                longitude=spot.get("longitude"),
                is_locker=spot.get("spotType") == "locker",
            )
            for spot in spots
        ]

    async def get_tracking_status(self, tracking_number: str) -> TrackingStatusResponse:
        """UNCONFIRMED endpoint shape — see spec A.2. HFD's plugin never
        calls a JSON status endpoint anywhere in its source; this method
        calls GET on the same /shipments/{id} path DELETE uses, by
        REST-symmetry inference only, and degrades any unrecognized
        response shape to ShipmentStatus.UNKNOWN rather than guessing."""
        resp = await self._client.get(f"/shipments/{tracking_number}")
        try:
            body = resp.json()
        except (_json.JSONDecodeError, ValueError):
            body = {}

        status = _HFD_STATUS_FIELD_MAP.get(body.get("status", ""), ShipmentStatus.UNKNOWN)
        return TrackingStatusResponse(
            provider=ProviderCode.HFD,
            tracking_number=tracking_number,
            status=status,
            raw=body,
        )
