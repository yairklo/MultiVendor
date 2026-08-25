from israel_shipping_sdk.base import BaseShippingProvider
from israel_shipping_sdk.providers.hfd import HFDProvider
from israel_shipping_sdk.providers.lionwheel import LionWheelProvider

# Field names each provider's credentials dict must have -- checked here
# (once, at config-write time and again at fulfillment time) rather than
# only relying on the provider constructor's own TypeError on a missing
# kwarg, so a vendor gets "missing client_number" instead of a raw
# TypeError leaking out of a third-party package.
REQUIRED_CREDENTIAL_FIELDS: dict[str, tuple[str, ...]] = {
    "hfd": ("auth_token", "client_number"),
    "lionwheel": ("api_key", "company_id"),
}


def validate_credentials(provider: str, credentials: dict) -> None:
    required = REQUIRED_CREDENTIAL_FIELDS.get(provider)
    if required is None:
        raise ValueError(f"Unknown shipping provider: {provider!r}")
    missing = [field for field in required if not credentials.get(field)]
    if missing:
        raise ValueError(f"Missing required {provider} credential field(s): {', '.join(missing)}")


def build_shipping_provider(provider: str, credentials: dict) -> BaseShippingProvider:
    validate_credentials(provider, credentials)
    if provider == "hfd":
        return HFDProvider(
            auth_token=credentials["auth_token"],
            client_number=int(credentials["client_number"]),
        )
    if provider == "lionwheel":
        return LionWheelProvider(
            api_key=credentials["api_key"],
            company_id=credentials["company_id"],
        )
    raise ValueError(f"Unknown shipping provider: {provider!r}")  # pragma: no cover -- unreachable, validate_credentials already raised
