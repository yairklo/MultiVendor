from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
from uuid import uuid4
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any],
    is_super_admin: bool = False,
    role: str = "user",
    store_role: Optional[str] = None,
) -> str:
    # Access tokens carry global `role` and optional login-time `store_role`
    # so the frontend proxy can gate /admin without a DB round-trip. Per-store
    # authorization is still re-checked against UserStoreMembership on every
    # admin API request -- these claims are a client hint, not the source of truth.
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {
        "exp": expire,
        "sub": str(subject),
        "typ": "access",
        "role": role,
        "is_super_admin": is_super_admin or role == "super_admin",
    }
    if store_role:
        to_encode["store_role"] = store_role
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: Union[str, Any]) -> tuple[str, str]:
    jti = uuid4().hex
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode(
        {"exp": expire, "sub": str(subject), "typ": "refresh", "jti": jti},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, jti

def refresh_token_ttl_seconds() -> int:
    return int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
