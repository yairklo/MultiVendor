"""Tenant custom-domain sync with Coolify's API (see
app/services/coolify_service.py) -- mocks the Coolify HTTP calls with
respx, same pattern as test_image_url_verifier.py / test_shipping.py."""
import json

import httpx
import pytest
import respx

from app.core.config import settings
from app.services.coolify_service import sync_tenant_domain

APP_UUID = "uuid-123"
API_BASE = "https://coolify.test/api/v1"
APP_URL = f"{API_BASE}/applications/{APP_UUID}"


@pytest.fixture
def coolify_enabled(monkeypatch):
    monkeypatch.setattr(settings, "COOLIFY_API_URL", API_BASE)
    monkeypatch.setattr(settings, "COOLIFY_API_TOKEN", "test-token")
    monkeypatch.setattr(settings, "COOLIFY_FRONTEND_APP_UUID", APP_UUID)
    monkeypatch.setattr(settings, "COOLIFY_FRONTEND_CONTAINER_NAME", "frontend")
    # sync_tenant_domain treats this hostname as the platform's own known
    # domain -- see _known_platform_domain's docstring.
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.test.local")


def _domains_response(domains: list[str]) -> httpx.Response:
    return httpx.Response(
        200,
        json={"docker_compose_domains": [{"domain": ",".join(domains), "container": "frontend"}]},
    )


def _sent_domains(patch_route) -> list[str]:
    body = json.loads(patch_route.calls.last.request.content)
    return body["docker_compose_domains"][0]["domain"].split(",")


@pytest.mark.asyncio
async def test_noop_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "COOLIFY_API_URL", None)
    monkeypatch.setattr(settings, "COOLIFY_API_TOKEN", None)
    monkeypatch.setattr(settings, "COOLIFY_FRONTEND_APP_UUID", None)
    await sync_tenant_domain(None, "tenant1.example.com")  # must not raise / call out


@pytest.mark.asyncio
async def test_noop_when_old_equals_new(coolify_enabled):
    await sync_tenant_domain("same.example.com", "same.example.com")  # must not call out


@pytest.mark.asyncio
@respx.mock
async def test_registers_new_domain_alongside_platform_domain(coolify_enabled):
    respx.get(APP_URL).mock(return_value=_domains_response(["app.test.local"]))
    patch_route = respx.patch(APP_URL).mock(return_value=httpx.Response(200, json={"uuid": APP_UUID}))

    await sync_tenant_domain(None, "tenant1.example.com")

    assert patch_route.called
    assert _sent_domains(patch_route) == ["app.test.local", "tenant1.example.com"]


@pytest.mark.asyncio
@respx.mock
async def test_replacing_domain_removes_old_and_adds_new(coolify_enabled):
    respx.get(APP_URL).mock(return_value=_domains_response(["app.test.local", "tenant1.example.com"]))
    patch_route = respx.patch(APP_URL).mock(return_value=httpx.Response(200, json={"uuid": APP_UUID}))

    await sync_tenant_domain("tenant1.example.com", "tenant2.example.com")

    assert _sent_domains(patch_route) == ["app.test.local", "tenant2.example.com"]


@pytest.mark.asyncio
@respx.mock
async def test_already_registered_domain_is_not_repatched(coolify_enabled):
    respx.get(APP_URL).mock(return_value=_domains_response(["app.test.local", "tenant1.example.com"]))
    patch_route = respx.patch(APP_URL).mock(return_value=httpx.Response(200))

    await sync_tenant_domain(None, "tenant1.example.com")

    assert not patch_route.called


@pytest.mark.asyncio
@respx.mock
async def test_aborts_when_platform_domain_missing_from_response(coolify_enabled):
    # Simulates a Coolify version whose response shape our parsing doesn't
    # match (see coollabsio/coolify#4999/#4326) -- must not guess and PATCH
    # a possibly-corrupt domain list.
    respx.get(APP_URL).mock(return_value=_domains_response(["something-unexpected.example"]))
    patch_route = respx.patch(APP_URL).mock(return_value=httpx.Response(200))

    await sync_tenant_domain(None, "tenant1.example.com")

    assert not patch_route.called


@pytest.mark.asyncio
@respx.mock
async def test_http_failure_is_swallowed_not_raised(coolify_enabled):
    respx.get(APP_URL).mock(return_value=httpx.Response(500))

    await sync_tenant_domain(None, "tenant1.example.com")  # must not raise
