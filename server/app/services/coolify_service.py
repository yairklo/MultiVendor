"""Optional integration: automatically route a tenant's custom domain
through Coolify's shared Traefik proxy, so it gets a Let's Encrypt cert
without an admin manually adding it in the Coolify UI.

Only relevant to the docker-compose.coolify.yaml deployment path -- a VPS
where Coolify's Traefik already fronts other apps, so this stack can't run
its own Caddy for on-demand TLS (see docs/DEPLOY_COOLIFY.md). A no-op
unless TRAEFIK_DYNAMIC_CONFIG_PATH/TRAEFIK_CERT_RESOLVER are both set, same
"safe disabled mode" pattern as SENTRY_DSN/GEMINI_API_KEY.

Mechanism: Traefik's file provider watches a directory (Coolify calls it
"Dynamic Configuration", Server -> Proxy -> Dynamic Configuration in the
Coolify UI) for extra routing config and reloads it live, with no Coolify
API call and no restart. This file is entirely ours -- a dedicated filename
inside that directory that Coolify itself never writes to -- so instead of
tracking incremental adds/removes against unknown external state (what an
earlier version of this module did against Coolify's REST API, which has
real open bugs: coollabsio/coolify#4999, #4326), it's simplest and safest
to just regenerate the whole file from our own database, our actual source
of truth, on every change. Any failure writing it is logged and swallowed,
never raised, so it can never block a tenant admin from saving their store
settings -- the manual fallback (add the domain by hand in Coolify's UI)
always still works if this silently fails.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

_ROUTER_SERVICE_NAME = "multivendor-tenants"
_NAME_SANITIZE_RE = re.compile(r"[^a-z0-9-]+")


def _enabled() -> bool:
    return bool(settings.TRAEFIK_DYNAMIC_CONFIG_PATH and settings.TRAEFIK_CERT_RESOLVER)


def _router_name(domain: str) -> str:
    # Traefik router names must be valid YAML/identifier-safe keys -- slugify
    # rather than trust the domain string verbatim.
    slug = _NAME_SANITIZE_RE.sub("-", domain.lower()).strip("-")
    return f"tenant-{slug}"


def _build_dynamic_config_yaml(domains: list[str]) -> str:
    if not domains:
        return "# No tenant custom domains registered -- nothing to route.\nhttp: {}\n"

    lines = ["http:", "  routers:"]
    for domain in domains:
        lines += [
            f"    {_router_name(domain)}:",
            f"      rule: \"Host(`{domain}`)\"",
            f"      entryPoints: [\"{settings.TRAEFIK_HTTPS_ENTRYPOINT}\"]",
            f"      service: {_ROUTER_SERVICE_NAME}",
            "      tls:",
            f"        certResolver: {settings.TRAEFIK_CERT_RESOLVER}",
        ]
    lines += [
        "  services:",
        f"    {_ROUTER_SERVICE_NAME}:",
        "      loadBalancer:",
        "        servers:",
        f"          - url: \"{settings.TRAEFIK_FRONTEND_UPSTREAM_URL}\"",
    ]
    return "\n".join(lines) + "\n"


def _write_file(path: str, content: str) -> None:
    # Write-then-rename so Traefik's file provider (which reloads on any
    # change to the file) never observes a half-written file mid-write.
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, path)


async def regenerate_traefik_dynamic_config(db: AsyncSession) -> None:
    """Best-effort: rewrites the Traefik dynamic-config file to list exactly
    the tenant custom domains currently active in our own database. Never
    raises -- see module docstring.
    """
    if not _enabled():
        return
    try:
        result = await db.execute(
            select(Tenant.custom_domain).where(Tenant.custom_domain.isnot(None), Tenant.status == "active")
        )
        domains = sorted({d.strip().lower() for (d,) in result.all() if d and d.strip()})
        content = _build_dynamic_config_yaml(domains)
        await asyncio.to_thread(_write_file, settings.TRAEFIK_DYNAMIC_CONFIG_PATH, content)
    except OSError:
        logger.exception(
            "Failed to write the Traefik dynamic-config file at %r -- tenant custom domains won't "
            "route until this is fixed or a domain is added manually in the Coolify UI as a fallback.",
            settings.TRAEFIK_DYNAMIC_CONFIG_PATH,
        )
