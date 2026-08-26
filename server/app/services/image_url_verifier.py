"""Reject image URLs that are not actually fetchable public images.

Shape checks (http(s) / /uploads/, no javascript:) live in normalize_asset_url.
This module is the second gate: HEAD/GET the URL and require an image
content-type, with SSRF guards so the model cannot make the server fetch
localhost or private networks.
"""
from __future__ import annotations

import asyncio
import ipaddress
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx

from fastapi import HTTPException

from app.core.config import settings

_MAX_REDIRECTS = 5
_TIMEOUT = httpx.Timeout(5.0, connect=3.0)
_USER_AGENT = "MultiVendor-image-check/1.0"
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan")
_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".bmp")


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return _ip_is_blocked(mapped)
    return False


def _assert_safe_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{url} is not an http(s) image URL")
    if parsed.username or parsed.password:
        raise ValueError("Image URL must not include credentials")
    if parsed.port not in (None, 80, 443):
        raise ValueError("Image URL must use port 80 or 443")
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_SUFFIXES):
        raise ValueError("Refusing to fetch an image from a private or local host")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and _ip_is_blocked(ip):
        raise ValueError("Refusing to fetch an image from a private or local host")


async def _resolve_host_ips(hostname: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(hostname, None)
    return [info[4][0] for info in infos]


async def _assert_host_resolves_public(hostname: str) -> None:
    try:
        ipaddress.ip_address(hostname)
        return
    except ValueError:
        pass
    try:
        ips = await _resolve_host_ips(hostname)
    except OSError as exc:
        raise ValueError(f"Could not resolve image host {hostname!r}") from exc
    if not ips:
        raise ValueError(f"Could not resolve image host {hostname!r}")
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _ip_is_blocked(ip):
            raise ValueError("Refusing to fetch an image from a private or local host")


def _looks_like_image_path(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _IMAGE_EXT)


def _assert_image_content_type(url: str, content_type: str | None) -> None:
    ctype = (content_type or "").split(";", 1)[0].strip().lower()
    if ctype.startswith("image/"):
        return
    if ctype in ("application/octet-stream", "") and _looks_like_image_path(url):
        return
    raise ValueError(
        f"{url} is not an image (content-type {ctype or 'unknown'}). "
        "Do not invent URLs — ask the user to upload a photo or paste a working image link."
    )


def _assert_local_upload(url: str) -> None:
    rel = url[len("/uploads/"):].lstrip("/").replace("\\", "/")
    if not rel or ".." in Path(rel).parts:
        raise ValueError(f"{url} is not a valid /uploads/... image path")
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    candidate = (upload_root / rel).resolve()
    if not candidate.is_relative_to(upload_root):
        raise ValueError(f"{url} is not a valid /uploads/... image path")
    if not candidate.is_file():
        raise ValueError(
            f"{url} does not exist on this store. Upload the file first, then use the returned /uploads/... URL."
        )


async def _fetch_headers(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.head(url)
    if response.status_code in (403, 405, 501):
        response = await client.get(url, headers={"Range": "bytes=0-255"})
    return response


async def _assert_remote_image(client: httpx.AsyncClient, url: str) -> None:
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        _assert_safe_http_url(current)
        host = urlparse(current).hostname or ""
        await _assert_host_resolves_public(host)
        try:
            response = await _fetch_headers(client, current)
        except httpx.HTTPError as exc:
            raise ValueError(
                f"{url} could not be fetched as an image ({exc}). "
                "Do not invent URLs — ask the user to upload a photo or paste a working image link."
            ) from exc
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise ValueError(f"{url} redirected without a Location header")
            current = urljoin(current, location)
            continue
        if response.status_code not in (200, 206):
            raise ValueError(
                f"{url} did not return an image (HTTP {response.status_code}). "
                "Do not invent URLs — ask the user to upload a photo or paste a working image link."
            )
        _assert_image_content_type(str(response.url) if response.url else current, response.headers.get("content-type"))
        return
    raise ValueError(f"{url} redirected too many times")


async def assert_reachable_image_urls(urls: Iterable[str | None]) -> None:
    """Raise ValueError if any URL is not a reachable public image.

    No-op when settings.VERIFY_REMOTE_IMAGE_URLS is false (the test suite).
    """
    if not settings.VERIFY_REMOTE_IMAGE_URLS:
        return
    cleaned = [u.strip() for u in urls if isinstance(u, str) and u.strip()]
    if not cleaned:
        return
    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": _USER_AGENT, "Accept": "image/*,*/*;q=0.1"},
    ) as client:
        for url in cleaned:
            if url.startswith("/uploads/"):
                _assert_local_upload(url)
                continue
            await _assert_remote_image(client, url)


async def require_reachable_image_urls(urls: Iterable[str | None]) -> None:
    """Like assert_reachable_image_urls, but raises HTTP 422 for REST/AI callers."""
    try:
        await assert_reachable_image_urls(urls)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
