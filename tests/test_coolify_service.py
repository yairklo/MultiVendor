"""Tenant custom-domain routing via a Traefik dynamic-config file (see
app/services/coolify_service.py) -- writes to a real temp file (via
tmp_path) and reads real Tenant rows back from the test DB, no HTTP
mocking needed since this no longer talks to any external API."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.tenant import Tenant
from app.services.coolify_service import regenerate_traefik_dynamic_config


@pytest.fixture
def traefik_enabled(tmp_path, monkeypatch):
    config_path = tmp_path / "multivendor-tenants.yaml"
    monkeypatch.setattr(settings, "TRAEFIK_DYNAMIC_CONFIG_PATH", str(config_path))
    monkeypatch.setattr(settings, "TRAEFIK_CERT_RESOLVER", "letsencrypt")
    monkeypatch.setattr(settings, "TRAEFIK_HTTPS_ENTRYPOINT", "https")
    monkeypatch.setattr(settings, "TRAEFIK_FRONTEND_UPSTREAM_URL", "http://frontend:3000")
    return config_path


async def _set_custom_domain(db_session, slug: str, domain: str | None, status: str = "active") -> None:
    tenant = (await db_session.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one()
    tenant.custom_domain = domain
    tenant.status = status
    await db_session.commit()


@pytest.mark.asyncio
async def test_noop_when_not_configured(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "TRAEFIK_DYNAMIC_CONFIG_PATH", None)
    monkeypatch.setattr(settings, "TRAEFIK_CERT_RESOLVER", None)
    config_path = tmp_path / "should-not-be-written.yaml"

    await regenerate_traefik_dynamic_config(db_session)

    assert not config_path.exists()


@pytest.mark.asyncio
async def test_writes_router_for_active_tenant_domain(db_session, traefik_enabled):
    await _set_custom_domain(db_session, "tenant-a", "shop-a.example.com")

    await regenerate_traefik_dynamic_config(db_session)

    content = traefik_enabled.read_text(encoding="utf-8")
    assert 'Host(`shop-a.example.com`)' in content
    assert "certResolver: letsencrypt" in content
    assert 'entryPoints: ["https"]' in content
    assert 'url: "http://frontend:3000"' in content


@pytest.mark.asyncio
async def test_suspended_tenant_domain_is_excluded(db_session, traefik_enabled):
    await _set_custom_domain(db_session, "tenant-a", "suspended-shop.example.com", status="suspended")

    await regenerate_traefik_dynamic_config(db_session)

    content = traefik_enabled.read_text(encoding="utf-8")
    assert "suspended-shop.example.com" not in content


@pytest.mark.asyncio
async def test_no_active_domains_writes_empty_but_valid_config(db_session, traefik_enabled):
    await regenerate_traefik_dynamic_config(db_session)

    content = traefik_enabled.read_text(encoding="utf-8")
    assert "http: {}" in content


@pytest.mark.asyncio
async def test_write_is_atomic_no_leftover_tmp_file(db_session, traefik_enabled):
    await _set_custom_domain(db_session, "tenant-a", "shop-a.example.com")

    await regenerate_traefik_dynamic_config(db_session)

    tmp_sibling = traefik_enabled.with_suffix(traefik_enabled.suffix + ".tmp")
    assert traefik_enabled.exists()
    assert not tmp_sibling.exists()


@pytest.mark.asyncio
async def test_domain_router_name_is_slugified(db_session, traefik_enabled):
    await _set_custom_domain(db_session, "tenant-a", "Shop-A.Example.COM")

    await regenerate_traefik_dynamic_config(db_session)

    content = traefik_enabled.read_text(encoding="utf-8")
    # Normalized to lowercase for the Host() match (see resolve_tenant_by_domain_service).
    assert 'Host(`shop-a.example.com`)' in content
    assert "tenant-shop-a-example-com:" in content
