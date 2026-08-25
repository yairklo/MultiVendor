import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient

from app.services.storage_service import save_digital_file

MINIMAL_PDF = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _upload(filename: str, content: bytes):
    upload = MagicMock()
    upload.filename = filename
    upload.read = AsyncMock(return_value=content)
    return upload


@pytest.mark.asyncio
async def test_save_digital_file_accepts_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage_service.settings.UPLOAD_DIR", str(tmp_path))
    url = await save_digital_file(_upload("my ebook.pdf", MINIMAL_PDF), tenant_id=7)
    assert url.startswith("/uploads/7/files/")
    assert url.endswith(".pdf")
    assert "my-ebook" in url
    assert (tmp_path / "7" / "files" / url.split("/")[-1]).read_bytes() == MINIMAL_PDF


@pytest.mark.asyncio
async def test_save_digital_file_rejects_html(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage_service.settings.UPLOAD_DIR", str(tmp_path))
    with pytest.raises(Exception) as exc:
        await save_digital_file(_upload("page.html", b"<html><script>alert(1)</script></html>"), tenant_id=7)
    assert getattr(exc.value, "status_code", None) == 400


@pytest.mark.asyncio
async def test_upload_digital_pdf_endpoint(async_client: AsyncClient, seed_tokens, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage_service.settings.UPLOAD_DIR", str(tmp_path))
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/uploads/file",
        headers=headers,
        files={"file": ("ebook.pdf", MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("/uploads/")
    assert url.endswith(".pdf")
    assert "ebook" in url


@pytest.mark.asyncio
async def test_upload_digital_file_endpoint_rejects_html(async_client: AsyncClient, seed_tokens, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.storage_service.settings.UPLOAD_DIR", str(tmp_path))
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/uploads/file",
        headers=headers,
        files={"file": ("page.html", b"<html><script>alert(1)</script></html>", "text/html")},
    )
    assert response.status_code == 400
