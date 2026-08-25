import pytest
from httpx import AsyncClient

from app.services.storefront_templates import AURORA


def _valid_pages():
    return AURORA["pages"]


def _valid_payload(**overrides):
    body = {
        "template_key": "lumen",
        "name": "Lumen",
        "tagline": "Bright, airy, product-first.",
        "swatch_json": {"bg": "#ffffff", "text": "#111827", "accent": "#0ea5e9"},
        "pages_json": _valid_pages(),
        "display_order": 10,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_tenant_admin_cannot_access_storefront_template_admin_routes(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    list_resp = await async_client.get("/api/v1/super-admin/storefront-templates", headers=headers)
    assert list_resp.status_code == 403

    create_resp = await async_client.post(
        "/api/v1/super-admin/storefront-templates", json=_valid_payload(), headers=headers
    )
    assert create_resp.status_code == 403

    put_resp = await async_client.put(
        "/api/v1/super-admin/storefront-templates/aurora",
        json={
            "name": "Hacked",
            "tagline": "nope",
            "swatch_json": {"bg": "#000", "text": "#fff", "accent": "#f00"},
            "pages_json": _valid_pages(),
        },
        headers=headers,
    )
    assert put_resp.status_code == 403

    patch_resp = await async_client.patch(
        "/api/v1/super-admin/storefront-templates/aurora",
        json={"is_active": False},
        headers=headers,
    )
    assert patch_resp.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_lists_inactive_templates(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}
    await async_client.patch(
        "/api/v1/super-admin/storefront-templates/aurora",
        json={"is_active": False},
        headers=headers,
    )
    response = await async_client.get("/api/v1/super-admin/storefront-templates", headers=headers)
    assert response.status_code == 200
    rows = response.json()["data"]
    keys = {row["template_key"] for row in rows}
    assert {"aurora", "atelier", "nova"} <= keys
    aurora = next(row for row in rows if row["template_key"] == "aurora")
    assert aurora["is_active"] is False
    assert aurora["is_builtin"] is True
    assert "pages_json" in aurora


@pytest.mark.asyncio
async def test_super_admin_rejects_invalid_pages_json(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}
    response = await async_client.post(
        "/api/v1/super-admin/storefront-templates",
        json=_valid_payload(
            pages_json={
                "home": {
                    "title": "Home",
                    "sections": [{"type": "not_a_real_section", "settings": {}}],
                }
            }
        ),
        headers=headers,
    )
    assert response.status_code == 422

    empty_sections = await async_client.post(
        "/api/v1/super-admin/storefront-templates",
        json=_valid_payload(template_key="blank", pages_json={"home": {"title": "Home", "sections": []}}),
        headers=headers,
    )
    assert empty_sections.status_code == 422


@pytest.mark.asyncio
async def test_super_admin_create_and_tenant_apply_still_works(async_client: AsyncClient, seed_tokens):
    super_headers = {"Authorization": seed_tokens["super_admin"]}
    tenant_headers = {"Authorization": seed_tokens["tenant_admin_a"]}

    created = await async_client.post(
        "/api/v1/super-admin/storefront-templates",
        json=_valid_payload(),
        headers=super_headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["template_key"] == "lumen"
    assert body["is_active"] is True
    assert body["is_builtin"] is False

    listed = await async_client.get("/api/v1/admin/store/tenant-a/ai/templates", headers=tenant_headers)
    assert listed.status_code == 200
    keys = {t["key"] for t in listed.json()}
    assert "lumen" in keys
    assert {"aurora", "atelier", "nova"} <= keys

    applied = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/templates/lumen/apply",
        headers=tenant_headers,
    )
    assert applied.status_code == 200, applied.text
    applied_body = applied.json()
    assert applied_body["template_key"] == "lumen"
    assert {p["page_key"] for p in applied_body["pages"]} == {"home", "about", "contact"}

    live_home = await async_client.get("/api/v1/store/tenant-a/pages/home")
    assert live_home.status_code == 200
    assert any(s["type"] == "hero_banner" for s in live_home.json()["sections"])


@pytest.mark.asyncio
async def test_super_admin_can_edit_and_reorder_builtin_without_deleting(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["super_admin"]}
    patched = await async_client.patch(
        "/api/v1/super-admin/storefront-templates/nova",
        json={"display_order": 99, "is_active": True},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["display_order"] == 99
    assert patched.json()["template_key"] == "nova"

    updated = await async_client.put(
        "/api/v1/super-admin/storefront-templates/nova",
        json={
            "name": "Nova",
            "tagline": "Bold, vivid, modern. (edited)",
            "swatch_json": {"bg": "#ffffff", "text": "#111827", "accent": "#f0653a"},
            "pages_json": _valid_pages(),
            "display_order": 2,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["tagline"] == "Bold, vivid, modern. (edited)"
    assert updated.json()["is_builtin"] is True

    deleted = await async_client.delete("/api/v1/super-admin/storefront-templates/nova", headers=headers)
    assert deleted.status_code == 405
