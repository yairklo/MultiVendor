"""Live image-URL checks: hallucinated http(s) links must not persist."""
import ipaddress

import httpx
import pytest
import respx

from app.core.config import settings
from app.services import image_url_verifier
from app.services.image_url_verifier import assert_reachable_image_urls
from app.services.ai_tool_executor import ToolGroundingContext, execute_tool

GOOD_URL = "https://images.example.com/good.jpg"
BAD_URL = "https://images.example.com/missing.jpg"
HTML_URL = "https://images.example.com/page.html"


@pytest.fixture
def verify_images(monkeypatch):
    monkeypatch.setattr(settings, "VERIFY_REMOTE_IMAGE_URLS", True)

    async def public_dns(hostname: str) -> list[str]:
        try:
            return [str(ipaddress.ip_address(hostname))]
        except ValueError:
            return ["1.1.1.1"]

    monkeypatch.setattr(image_url_verifier, "_resolve_host_ips", public_dns)


@pytest.mark.asyncio
async def test_private_and_localhost_image_hosts_are_rejected(verify_images):
    for url in (
        "http://127.0.0.1/secret.png",
        "http://localhost/secret.png",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.4/img.png",
        "https://example.com:8443/img.png",
    ):
        with pytest.raises(ValueError, match="[Rr]efusing|port 80 or 443"):
            await assert_reachable_image_urls([url])


@pytest.mark.asyncio
async def test_hostname_that_resolves_to_loopback_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "VERIFY_REMOTE_IMAGE_URLS", True)

    async def loopback(_hostname: str) -> list[str]:
        return ["127.0.0.1"]

    monkeypatch.setattr(image_url_verifier, "_resolve_host_ips", loopback)
    with pytest.raises(ValueError, match="private or local"):
        await assert_reachable_image_urls(["https://evil.example.com/x.png"])


@pytest.mark.asyncio
async def test_missing_upload_path_is_rejected(verify_images):
    with pytest.raises(ValueError, match="does not exist"):
        await assert_reachable_image_urls(["/uploads/999/not-a-real-file.png"])


@pytest.mark.asyncio
@respx.mock
async def test_http_404_and_html_content_are_rejected(verify_images):
    respx.head(BAD_URL).mock(return_value=httpx.Response(404))
    respx.head(HTML_URL).mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"})
    )
    with pytest.raises(ValueError, match="HTTP 404"):
        await assert_reachable_image_urls([BAD_URL])
    with pytest.raises(ValueError, match="not an image"):
        await assert_reachable_image_urls([HTML_URL])


@pytest.mark.asyncio
@respx.mock
async def test_reachable_jpeg_is_accepted(verify_images):
    respx.head(GOOD_URL).mock(
        return_value=httpx.Response(200, headers={"content-type": "image/jpeg"})
    )
    await assert_reachable_image_urls([GOOD_URL])


@pytest.mark.asyncio
@respx.mock
async def test_update_product_rejects_a_404_image_and_keeps_the_gallery(db_session, verify_images):
    respx.head(BAD_URL).mock(return_value=httpx.Response(404))
    context = ToolGroundingContext()
    await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session, context)
    before = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert before.output["images"] == []

    result = await execute_tool(
        "update_product",
        {"product_id": 1, "images": [BAD_URL]},
        "tenant-a",
        db_session,
        context,
    )
    assert result.is_error is True
    assert result.error_type == "ValidationFailed"
    assert "404" in str(result.output)

    after = await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session)
    assert after.output["images"] == []


@pytest.mark.asyncio
@respx.mock
async def test_update_product_persists_only_after_the_url_returns_an_image(db_session, verify_images):
    respx.head(GOOD_URL).mock(
        return_value=httpx.Response(200, headers={"content-type": "image/jpeg"})
    )
    context = ToolGroundingContext()
    await execute_tool("get_product", {"product_id": 1}, "tenant-a", db_session, context)
    result = await execute_tool(
        "update_product",
        {"product_id": 1, "images": [GOOD_URL]},
        "tenant-a",
        db_session,
        context,
    )
    assert result.is_error is False
    assert result.output["images"] == [GOOD_URL]
    assert result.output["primary_image_url"] == GOOD_URL
