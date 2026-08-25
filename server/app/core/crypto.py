import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _require_key() -> Fernet:
    if not settings.SHIPPING_CREDENTIALS_ENCRYPTION_KEY:
        raise RuntimeError("SHIPPING_CREDENTIALS_ENCRYPTION_KEY is not configured")
    return Fernet(settings.SHIPPING_CREDENTIALS_ENCRYPTION_KEY.encode("utf-8"))


def encrypt_json(data: dict) -> str:
    """Encrypts a small JSON-serializable dict (courier API credentials) for
    storage in TenantShippingConfig.credentials_encrypted. Never store the
    result anywhere logs might capture it -- treat it the same as the
    plaintext it replaces."""
    token = _require_key().encrypt(json.dumps(data).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_json(token: str) -> dict:
    try:
        payload = _require_key().decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        # Wrong/rotated SHIPPING_CREDENTIALS_ENCRYPTION_KEY, or a corrupted
        # column -- either way this is an ops problem, not a client error,
        # so it's raised as-is for the caller to turn into a 500, not
        # silently swallowed into "no credentials configured".
        raise RuntimeError("Failed to decrypt shipping credentials") from exc
    return json.loads(payload.decode("utf-8"))
