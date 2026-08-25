class ShippingException(Exception):
    """Root of the hierarchy. Carries the provider code and, where
    available, the raw HTTP status + body for debugging."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        raw: object = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.raw = raw


class ProviderAuthError(ShippingException):
    """401/403 from a provider — bad or expired token."""


class AddressValidationError(ShippingException):
    """Raised by the Gov.il validator, or by a provider that rejects an
    address outright."""

    def __init__(self, message: str, *, field: str, **kwargs) -> None:
        super().__init__(message, **kwargs)
        self.field = field


class LabelGenerationError(ShippingException):
    """Shipment was accepted but no label URL/bytes were returned."""


class ShipmentNotFoundError(ShippingException):
    """Tracking number / task id does not exist at the provider."""


class UnsupportedOperationError(ShippingException):
    """Operation has no provider-side equivalent."""


class ProviderRateLimitError(ShippingException):
    """429 from a provider."""
