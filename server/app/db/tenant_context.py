from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import wraps
from typing import Iterator

_tenant_id: ContextVar[int | None] = ContextVar("tenant_id", default=None)
_unscoped: ContextVar[bool] = ContextVar("tenant_unscoped", default=False)


class TenantContextRequired(RuntimeError):
    """A tenant-scoped query/write ran with no bound tenant and no unscoped()."""


class TenantIsolationError(RuntimeError):
    """An explicit write tried to cross the bound tenant."""


def get_current_tenant_id() -> int | None:
    return _tenant_id.get()


def bind_tenant(tenant_id: int) -> Token:
    return _tenant_id.set(int(tenant_id))


def reset_tenant(token: Token) -> None:
    _tenant_id.reset(token)


def is_unscoped() -> bool:
    return _unscoped.get()


@contextmanager
def unscoped() -> Iterator[None]:
    """Opt out of tenant auto-filter for the platform / identity plane."""
    token = _unscoped.set(True)
    try:
        yield
    finally:
        _unscoped.reset(token)


def platform_plane(fn):
    """Decorator: this function is allowed to see every tenant."""

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        with unscoped():
            return await fn(*args, **kwargs)

    return wrapper
