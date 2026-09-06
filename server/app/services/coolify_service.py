"""Optional integration: automatically register a tenant's custom domain
with Coolify's own shared proxy, so it gets a Let's Encrypt cert without an
admin manually adding it in the Coolify UI.

Only relevant to the docker-compose.coolify.yaml deployment path -- a VPS
where Coolify's Traefik already fronts other apps, so this stack can't run
its own Caddy for on-demand TLS (see docs/DEPLOY_COOLIFY.md). A no-op
unless COOLIFY_API_URL/COOLIFY_API_TOKEN/COOLIFY_FRONTEND_APP_UUID are all
set, same "safe disabled mode" pattern as SENTRY_DSN/GEMINI_API_KEY.

Coolify's API for updating a Docker Compose application's domains has real,
open bugs in some versions (coollabsio/coolify#4999, #4326) -- this is
deliberately best-effort: any failure is logged and swallowed, never
raised, so a Coolify hiccup can never block a tenant admin from saving
their store settings. The existing manual fallback (add the domain by hand
in Coolify's UI) always still works if this silently fails.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _enabled() -> bool:
    return bool(
        settings.COOLIFY_API_URL
        and settings.COOLIFY_API_TOKEN
        and settings.COOLIFY_FRONTEND_APP_UUID
    )


def _known_platform_domain() -> str | None:
    """The platform's own frontend hostname, derived from FRONTEND_URL
    (already required config, so this needs no new setting). Used as a
    sanity check below: this domain was registered on the frontend app in
    Coolify during initial setup (docs/DEPLOY_COOLIFY.md step 4), so it
    must always show up in whatever _fetch_current_domains parses out of
    Coolify's response -- if it doesn't, our parsing almost certainly
    doesn't match this Coolify version's actual response shape, and it's
    safer to skip the update than PATCH a guess that could wipe out every
    domain currently registered.
    """
    return (urlparse(settings.FRONTEND_URL).hostname or "").lower() or None


def _domains_url() -> str:
    return f"/applications/{settings.COOLIFY_FRONTEND_APP_UUID}"


async def _fetch_current_domains(client: httpx.AsyncClient) -> list[str]:
    """Reads the frontend container's current docker_compose_domains so the
    PATCH below can send the full merged list back -- Coolify's domain
    update replaces the whole array rather than appending to it, so
    fetching first is what stops it from wiping out the platform's own
    domain or every other tenant's domain already registered.
    """
    response = await client.get(_domains_url())
    response.raise_for_status()
    data = response.json()
    entries = data.get("docker_compose_domains") or []
    domains: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("container") != settings.COOLIFY_FRONTEND_CONTAINER_NAME:
            continue
        domains.extend(d.strip().lower() for d in (entry.get("domain") or "").split(",") if d.strip())
    return domains


async def _put_domains(client: httpx.AsyncClient, domains: list[str]) -> None:
    deduped = list(dict.fromkeys(domains))  # preserve order, drop duplicates
    response = await client.patch(
        _domains_url(),
        json={
            "docker_compose_domains": [
                {"domain": ",".join(deduped), "container": settings.COOLIFY_FRONTEND_CONTAINER_NAME}
            ]
        },
    )
    response.raise_for_status()


async def sync_tenant_domain(old_domain: str | None, new_domain: str | None) -> None:
    """Best-effort: reflects a tenant's custom_domain change onto the
    frontend app's domain list in Coolify -- registers `new_domain` and, if
    it's a replacement rather than a first-time set, removes `old_domain`.
    Never raises -- see module docstring.
    """
    if not _enabled():
        return
    old_domain = (old_domain or "").strip().lower() or None
    new_domain = (new_domain or "").strip().lower() or None
    if old_domain == new_domain:
        return

    try:
        async with httpx.AsyncClient(
            base_url=settings.COOLIFY_API_URL,
            headers={"Authorization": f"Bearer {settings.COOLIFY_API_TOKEN}"},
            timeout=_TIMEOUT,
        ) as client:
            current = await _fetch_current_domains(client)

            platform_domain = _known_platform_domain()
            if platform_domain and platform_domain not in current:
                logger.error(
                    "Coolify's reported domains for app %s don't include this platform's own domain "
                    "(%s) -- the response shape probably doesn't match what this integration expects "
                    "(see coollabsio/coolify#4999, #4326). Skipping the automatic update; add %r "
                    "manually in the Coolify UI instead.",
                    settings.COOLIFY_FRONTEND_APP_UUID, platform_domain, new_domain,
                )
                return

            updated = [d for d in current if d != old_domain] if old_domain else list(current)
            if new_domain and new_domain not in updated:
                updated.append(new_domain)
            if updated == current:
                return

            await _put_domains(client, updated)
    except httpx.HTTPError:
        logger.exception(
            "Failed to sync tenant domain (old=%r, new=%r) with Coolify -- add/remove it manually "
            "in the Coolify UI as a fallback.",
            old_domain, new_domain,
        )
