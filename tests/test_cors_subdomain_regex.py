"""CORS_ALLOWED_ORIGIN_REGEX (see app/core/config.py, app/main.py) -- for a
subdomain-per-tenant deploy where the set of allowed origins (one per store
subdomain) is unbounded and unknown in advance, so the fixed
CORS_ALLOWED_ORIGINS list can't enumerate them. Builds a throwaway
FastAPI+CORSMiddleware app (not the real app.main singleton, which is
already constructed by the time tests run) to verify Starlette's actual
regex-matching behavior empirically rather than assume it.
"""
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

# The exact pattern documented as the recommended example in
# core/config.py's CORS_ALLOWED_ORIGIN_REGEX comment.
EXAMPLE_REGEX = r"^https://([a-z0-9-]+\.)*example\.com$"


def _build_app(regex: str | None) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        # `regex or None`, matching app/main.py's actual normalization -- see
        # test_raw_empty_string_regex_matches_nothing_in_starlette below for
        # why "" is already safe even without this.
        allow_origin_regex=regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


async def _cors_headers_for_origin(app: FastAPI, origin: str) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/ping", headers={"Origin": origin})
        return response.headers


@pytest.mark.asyncio
async def test_bare_domain_is_allowed():
    headers = await _cors_headers_for_origin(_build_app(EXAMPLE_REGEX), "https://example.com")
    assert headers.get("access-control-allow-origin") == "https://example.com"


@pytest.mark.asyncio
async def test_tenant_subdomain_is_allowed():
    headers = await _cors_headers_for_origin(_build_app(EXAMPLE_REGEX), "https://tenant-a.example.com")
    assert headers.get("access-control-allow-origin") == "https://tenant-a.example.com"


@pytest.mark.asyncio
async def test_deeper_subdomain_is_allowed():
    headers = await _cors_headers_for_origin(_build_app(EXAMPLE_REGEX), "https://shop.tenant-a.example.com")
    assert headers.get("access-control-allow-origin") == "https://shop.tenant-a.example.com"


@pytest.mark.asyncio
async def test_unrelated_domain_is_rejected():
    headers = await _cors_headers_for_origin(_build_app(EXAMPLE_REGEX), "https://evil.com")
    assert "access-control-allow-origin" not in headers


@pytest.mark.asyncio
async def test_lookalike_suffix_domain_is_rejected():
    # Anchoring matters: without the trailing $, "example.com.evil.com" or
    # "notexample.com" style suffixes could slip through.
    headers = await _cors_headers_for_origin(_build_app(EXAMPLE_REGEX), "https://example.com.evil.com")
    assert "access-control-allow-origin" not in headers


@pytest.mark.asyncio
async def test_http_scheme_is_rejected_when_pattern_requires_https():
    headers = await _cors_headers_for_origin(_build_app(EXAMPLE_REGEX), "http://tenant-a.example.com")
    assert "access-control-allow-origin" not in headers


@pytest.mark.asyncio
async def test_none_regex_matches_nothing_extra():
    # Sanity check on the "unset -> unchanged behavior" claim in
    # core/config.py's comment: allow_origin_regex=None must not accidentally
    # allow-all.
    headers = await _cors_headers_for_origin(_build_app(None), "https://tenant-a.example.com")
    assert "access-control-allow-origin" not in headers


@pytest.mark.asyncio
async def test_raw_empty_string_regex_matches_nothing_in_starlette():
    # Pins Starlette's actual behavior for an un-guarded "" (the value
    # CORS_ALLOWED_ORIGIN_REGEX takes on via docker-compose's `${VAR:-}`
    # passthrough default when unset): CORSMiddleware matches with
    # `.fullmatch()`, and an empty pattern only fullmatches an empty string,
    # never a real Origin header -- so this is already a safe no-op even
    # without app/main.py's `or None` normalization, confirmed here rather
    # than assumed. (An earlier version of this test/comment wrongly assumed
    # `.match()` semantics, where an empty pattern DOES match everything --
    # this test is what caught that mistake before it shipped.)
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex="",  # the un-normalized raw value -- see docstring above
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    headers = await _cors_headers_for_origin(app, "https://totally-unrelated-evil.com")
    assert "access-control-allow-origin" not in headers


@pytest.mark.asyncio
async def test_empty_string_regex_through_our_normalization_still_matches_nothing():
    # The real-world case: an unset CORS_ALLOWED_ORIGIN_REGEX reaches
    # app/main.py as "" via docker-compose's `${VAR:-}` passthrough default,
    # not as None. _build_app applies the same `regex or None` normalization
    # main.py does -- same safe outcome as the raw "" case above, just via an
    # explicit None instead of relying on fullmatch's empty-pattern quirk.
    headers = await _cors_headers_for_origin(_build_app(""), "https://totally-unrelated-evil.com")
    assert "access-control-allow-origin" not in headers
