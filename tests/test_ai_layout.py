import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.tenant import Tenant, SubscriptionPlan
from app.services.ai_tool_executor import execute_tool


@pytest.mark.asyncio
async def test_status_defaults_to_mock_without_gemini_key(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/ai/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"


@pytest.mark.asyncio
async def test_chat_layout_edit_creates_and_updates_a_page(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}

    # "landing" doesn't exist yet for tenant-a — this also covers the
    # upsert-creates-a-new-page path (distinct from the pre-seeded "home" page).
    create_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner and add a gallery", "page_key": "landing", "page_type": "static_page"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["used_provider"] == "mock"
    assert body["page"] is not None
    types_created = [s["type"] for s in body["page"]["sections"]]
    assert types_created == ["hero_banner", "gallery"]

    edit_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "move the gallery above the hero banner", "page_key": "landing", "page_type": "static_page"},
        headers=headers,
    )
    assert edit_resp.status_code == 200
    types_after_move = [s["type"] for s in edit_resp.json()["page"]["sections"]]
    assert types_after_move == ["gallery", "hero_banner"]

    targets_resp = await async_client.get("/api/v1/admin/store/tenant-a/ai/page-targets", headers=headers)
    assert targets_resp.status_code == 200
    assert any(t["page_key"] == "landing" and t["section_count"] == 2 for t in targets_resp.json())
    # The seed data's pre-existing "home" page for tenant-a should also still be listed.
    assert any(t["page_key"] == "home" for t in targets_resp.json())

    # Draft edits never reach the public storefront until explicitly published.
    assert edit_resp.json()["page"]["has_unpublished_changes"] is True
    unpublished_resp = await async_client.get("/api/v1/store/tenant-a/pages/landing")
    assert unpublished_resp.status_code == 404

    publish_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/publish?page_key=landing&page_type=static_page", headers=headers
    )
    assert publish_resp.status_code == 200
    assert publish_resp.json()["has_unpublished_changes"] is False

    public_resp = await async_client.get("/api/v1/store/tenant-a/pages/landing")
    assert public_resp.status_code == 200
    assert [s["type"] for s in public_resp.json()["sections"]] == ["gallery", "hero_banner"]

    # Regression check: once a page has been published (so its published_at is a
    # real datetime, not None), a *subsequent* chat turn must still succeed. This
    # caught a real bug — the tool executor's schema.model_dump() (no mode="json")
    # left published_at as a raw Python datetime inside the tool_call output, which
    # then failed to serialize when persisted into the ai_conversations.messages
    # JSON column, 500ing every chat call on any previously-published page.
    post_publish_edit = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a text block", "page_key": "landing", "page_type": "static_page"},
        headers=headers,
    )
    assert post_publish_edit.status_code == 200


@pytest.mark.asyncio
async def test_public_page_read_only_serves_static_pages(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a text block", "page_key": "product_template", "page_type": "template"},
        headers=headers,
    )
    # A template exists, but the public route only ever serves static_page.
    response = await async_client.get("/api/v1/store/tenant-a/pages/product_template")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_admin_cannot_read_or_chat_on_another_tenants_pages(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}

    targets_resp = await async_client.get("/api/v1/admin/store/tenant-b/ai/page-targets", headers=headers_a)
    assert targets_resp.status_code == 403

    chat_resp = await async_client.post(
        "/api/v1/admin/store/tenant-b/ai/chat",
        json={"message": "add a hero banner", "page_key": "home", "page_type": "static_page"},
        headers=headers_a,
    )
    assert chat_resp.status_code == 403


@pytest.mark.asyncio
async def test_customer_cannot_use_admin_ai_endpoints(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    response = await async_client.get("/api/v1/admin/store/tenant-a/ai/page-targets", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_page_sections_drops_unrecognized_button_action_type(async_client: AsyncClient, db_session):
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "home",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "button_group",
                    "settings": {
                        "buttons": [
                            {"label": "Legit", "actionType": "NAVIGATE", "actionPayload": {"href": "/shop"}},
                            {"label": "Malicious", "actionType": "RUN_ARBITRARY_JS", "actionPayload": {"code": "alert(1)"}},
                        ]
                    },
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    buttons = result.output["sections"][0]["settings"]["buttons"]
    assert [b["label"] for b in buttons] == ["Legit"]


@pytest.mark.asyncio
async def test_create_product_tool_respects_subscription_limit(async_client: AsyncClient, db_session):
    tenant_result = await db_session.execute(select(Tenant).where(Tenant.slug == "tenant-a"))
    tenant = tenant_result.scalar_one()
    plan_result = await db_session.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan_id))
    plan = plan_result.scalar_one()
    plan.max_products = 1  # tenant-a is seeded with 1 product already
    await db_session.commit()

    result = await execute_tool(
        "create_product",
        {
            "name": {"en": "AI Product", "he": "מוצר AI"},
            "slug": "ai-product",
            "base_price": 42.0,
            "variants": [{"sku": "AI-SKU-1", "stock_quantity": 5}],
            "images": [],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is True
    assert "Maximum number of products" in result.output["error"]


@pytest.mark.asyncio
async def test_page_background_color_is_page_level_not_per_section(async_client: AsyncClient, seed_tokens):
    # "change the page background to black" — the mock agent's dedicated
    # page-background phrase, distinct from any per-section settings.background_color.
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "change the page background to black", "page_key": "bg-test", "page_type": "static_page"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"]["background_color"] == "black"
    # None of the (empty) sections should have picked up a background_color themselves.
    assert body["page"]["sections"] == []

    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/publish?page_key=bg-test&page_type=static_page", headers=headers
    )
    public_resp = await async_client.get("/api/v1/store/tenant-a/pages/bg-test")
    assert public_resp.status_code == 200
    assert public_resp.json()["background_color"] == "black"


@pytest.mark.asyncio
async def test_page_background_color_persists_across_unrelated_edits_and_can_be_cleared(
    async_client: AsyncClient, db_session
):
    from app.services.store_page_service import upsert_page_sections_service

    schema = await upsert_page_sections_service(
        "tenant-a", "bg-persist", "static_page", [], db_session, background_color="red"
    )
    assert schema.background_color == "red"

    # An update that doesn't mention background_color at all must leave it alone.
    schema = await upsert_page_sections_service(
        "tenant-a", "bg-persist", "static_page",
        [{"type": "text_block", "settings": {"heading": "Hi"}}],
        db_session,
    )
    assert schema.background_color == "red"

    # An explicit empty string clears it back to the default.
    schema = await upsert_page_sections_service(
        "tenant-a", "bg-persist", "static_page", [], db_session, background_color=""
    )
    assert schema.background_color is None


@pytest.mark.asyncio
async def test_publish_is_scoped_to_the_authenticated_tenant(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}

    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner", "page_key": "publish-scope", "page_type": "static_page"},
        headers=headers_a,
    )
    # tenant-b's own admin can't publish tenant-a's draft, even by guessing the page_key.
    cross_tenant_resp = await async_client.post(
        "/api/v1/admin/store/tenant-b/ai/publish?page_key=publish-scope&page_type=static_page", headers=headers_b
    )
    assert cross_tenant_resp.status_code == 404

    own_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/publish?page_key=publish-scope&page_type=static_page", headers=headers_a
    )
    assert own_resp.status_code == 200


@pytest.mark.asyncio
async def test_page_versions_listing_is_capped_independent_of_write_side_pruning(
    async_client: AsyncClient, seed_tokens, db_session
):
    # _snapshot_version already prunes stored rows to MAX_VERSIONS_PER_PAGE on
    # write, but the read endpoint must not rely solely on that staying correct
    # — insert more than the cap directly, bypassing the pruning code path
    # entirely, and confirm the listing query itself still clamps the result.
    from app.models.tenant import Tenant
    from app.models.store_page import StorePage, StorePageVersion
    from app.services.store_page_service import MAX_VERSIONS_PER_PAGE

    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner", "page_key": "many-versions", "page_type": "static_page"},
        headers=headers,
    )

    tenant_id = (await db_session.execute(select(Tenant.id).where(Tenant.slug == "tenant-a"))).scalar_one()
    page = (await db_session.execute(
        select(StorePage).where(
            StorePage.tenant_id == tenant_id, StorePage.page_key == "many-versions", StorePage.page_type == "static_page"
        )
    )).scalar_one()

    for i in range(MAX_VERSIONS_PER_PAGE + 15):
        db_session.add(StorePageVersion(
            store_page_id=page.id, tenant_id=tenant_id, page_key="many-versions", page_type="static_page",
            title=f"Version {i}", sections=[],
        ))
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/page-versions?page_key=many-versions&page_type=static_page", headers=headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == MAX_VERSIONS_PER_PAGE


@pytest.mark.asyncio
async def test_page_version_history_snapshots_on_edit_and_supports_revert(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}

    create_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner", "page_key": "versioned", "page_type": "static_page"},
        headers=headers,
    )
    assert create_resp.status_code == 200

    # Creating the page for the first time takes no snapshot — there's nothing prior to save.
    versions_after_create = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/page-versions?page_key=versioned&page_type=static_page", headers=headers
    )
    assert versions_after_create.json() == []

    edit_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "make the hero banner larger", "page_key": "versioned", "page_type": "static_page"},
        headers=headers,
    )
    assert edit_resp.json()["page"]["sections"][0]["settings"]["size"] == "large"

    versions_after_edit = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/page-versions?page_key=versioned&page_type=static_page", headers=headers
    )
    versions = versions_after_edit.json()
    assert len(versions) == 1  # the pre-edit ("medium") state was snapshotted

    revert_resp = await async_client.post(
        f"/api/v1/admin/store/tenant-a/ai/page-versions/{versions[0]['id']}/revert"
        "?page_key=versioned&page_type=static_page",
        headers=headers,
    )
    assert revert_resp.status_code == 200
    assert revert_resp.json()["sections"][0]["settings"]["size"] == "medium"

    # The revert itself was snapshotted too, so it can be undone.
    versions_after_revert = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/page-versions?page_key=versioned&page_type=static_page", headers=headers
    )
    assert len(versions_after_revert.json()) == 2


@pytest.mark.asyncio
async def test_page_versions_and_revert_are_scoped_to_the_authenticated_tenant(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}

    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner", "page_key": "version-scope", "page_type": "static_page"},
        headers=headers_a,
    )
    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "make it larger", "page_key": "version-scope", "page_type": "static_page"},
        headers=headers_a,
    )
    versions = (await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/page-versions?page_key=version-scope&page_type=static_page",
        headers=headers_a,
    )).json()
    assert len(versions) == 1
    version_id = versions[0]["id"]

    # tenant-b can't see tenant-a's version history for the same page_key...
    cross_tenant_list = await async_client.get(
        "/api/v1/admin/store/tenant-b/ai/page-versions?page_key=version-scope&page_type=static_page",
        headers=headers_b,
    )
    assert cross_tenant_list.json() == []

    # ...nor revert to tenant-a's version id, even knowing it.
    cross_tenant_revert = await async_client.post(
        f"/api/v1/admin/store/tenant-b/ai/page-versions/{version_id}/revert"
        "?page_key=version-scope&page_type=static_page",
        headers=headers_b,
    )
    assert cross_tenant_revert.status_code == 404


@pytest.mark.asyncio
async def test_conversation_persists_across_turns_and_never_leaks_between_tenants(
    async_client: AsyncClient, seed_tokens
):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}

    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a hero banner", "page_key": "convo-test", "page_type": "static_page"},
        headers=headers_a,
    )
    await async_client.post(
        "/api/v1/admin/store/tenant-a/ai/chat",
        json={"message": "add a gallery too", "page_key": "convo-test", "page_type": "static_page"},
        headers=headers_a,
    )

    convo_a = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_key=convo-test&page_type=static_page", headers=headers_a
    )
    assert convo_a.status_code == 200
    messages = convo_a.json()["messages"]
    assert len(messages) == 4  # user/assistant pair per turn
    assert messages[0]["text"] == "add a hero banner"
    assert messages[2]["text"] == "add a gallery too"

    # Same page_key, different tenant — must see nothing, even though the tenant
    # is a valid admin of their own store. This is the core "no leak" guarantee.
    convo_b = await async_client.get(
        "/api/v1/admin/store/tenant-b/ai/conversation?page_key=convo-test&page_type=static_page", headers=headers_b
    )
    assert convo_b.status_code == 200
    assert convo_b.json()["messages"] == []

    # Clearing genuinely resets it, not just what the frontend happens to show.
    clear_resp = await async_client.delete(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_key=convo-test&page_type=static_page", headers=headers_a
    )
    assert clear_resp.status_code == 204
    convo_after_clear = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/conversation?page_key=convo-test&page_type=static_page", headers=headers_a
    )
    assert convo_after_clear.json()["messages"] == []


@pytest.mark.asyncio
async def test_create_product_tool_is_scoped_to_the_authenticated_tenant(async_client: AsyncClient, db_session):
    # Even if a caller tried to smuggle a different tenant/vendor id into the
    # tool args, execute_tool only ever reads the tenant_slug parameter passed
    # in by the authenticated request path — never anything from raw_input.
    result = await execute_tool(
        "create_product",
        {
            "tenant_id": 2,
            "tenant_slug": "tenant-b",
            "name": {"en": "Smuggled Product", "he": "מוצר"},
            "slug": "smuggled-product",
            "base_price": 10.0,
            "variants": [{"sku": "SMUGGLE-1", "stock_quantity": 5}],
            "images": [],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    assert result.output["tenant_id"] == 1  # tenant-a, not the smuggled tenant-b


# ---------------------------------------------------------------------------
# Nested sections (grid_container / two_column_layout)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_page_sections_sanitizes_nested_grid_container_children(async_client: AsyncClient, db_session):
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "nested-grid",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "grid_container",
                    "settings": {"columns": 3, "design_variant": "accent"},
                    "children": [
                        {"type": "text_block", "settings": {"heading": "One"}},
                        {"type": "text_block", "settings": {"heading": "Two"}},
                    ],
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    grid = result.output["sections"][0]
    assert grid["type"] == "grid_container"
    assert grid["settings"]["design_variant"] == "accent"
    children = grid["children"]
    assert len(children) == 2
    assert all(c["id"] for c in children)  # ids generated
    assert children[0]["id"] != children[1]["id"]  # unique even though never supplied


@pytest.mark.asyncio
async def test_update_page_sections_rejects_invalid_nested_section_type(async_client: AsyncClient, db_session):
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "nested-bad-type",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "grid_container",
                    "settings": {"columns": 2},
                    "children": [{"type": "not_a_real_type", "settings": {}}],
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is True
    assert "Invalid section type" in result.output["error"]


@pytest.mark.asyncio
async def test_update_page_sections_enforces_max_nesting_depth(async_client: AsyncClient, db_session):
    # grid_container -> children[0] grid_container -> children[0] grid_container -> children[0]
    # grid_container: one level past MAX_SECTION_NESTING_DEPTH (3).
    def _grid(inner):
        return {"type": "grid_container", "settings": {"columns": 1}, "children": [inner] if inner else []}

    too_deep = _grid(_grid(_grid(_grid({"type": "text_block", "settings": {}}))))
    result = await execute_tool(
        "update_page_sections",
        {"page_key": "too-deep", "page_type": "static_page", "sections": [too_deep]},
        "tenant-a",
        db_session,
    )
    assert result.is_error is True
    assert "nesting too deep" in result.output["error"].lower()


@pytest.mark.asyncio
async def test_update_page_sections_drops_unrecognized_button_action_type_when_nested(
    async_client: AsyncClient, db_session
):
    # Proves the recursive sanitizer reuses the exact same button_group sanitization as the
    # top-level path — not a parallel, weaker code path for nested content.
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "nested-button-sanitize",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "grid_container",
                    "settings": {"columns": 2},
                    "children": [
                        {
                            "type": "button_group",
                            "settings": {
                                "buttons": [
                                    {"label": "Legit", "actionType": "NAVIGATE", "actionPayload": {"href": "/shop"}},
                                    {"label": "Malicious", "actionType": "RUN_ARBITRARY_JS"},
                                ]
                            },
                        }
                    ],
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    nested_buttons = result.output["sections"][0]["children"][0]["settings"]["buttons"]
    assert [b["label"] for b in nested_buttons] == ["Legit"]


@pytest.mark.asyncio
async def test_update_page_sections_sanitizes_two_column_layout_zones(async_client: AsyncClient, db_session):
    result = await execute_tool(
        "update_page_sections",
        {
            "page_key": "two-col",
            "page_type": "static_page",
            "sections": [
                {
                    "type": "two_column_layout",
                    "settings": {},
                    "zones": {
                        "left": [{"type": "text_block", "settings": {"heading": "Left"}}],
                        "right": [{"type": "text_block", "settings": {"heading": "Right"}}],
                        "middle": [{"type": "text_block", "settings": {"heading": "Dropped"}}],
                    },
                }
            ],
        },
        "tenant-a",
        db_session,
    )
    assert result.is_error is False
    zones = result.output["sections"][0]["zones"]
    assert set(zones.keys()) == {"left", "right"}  # unrecognized "middle" key dropped
    assert zones["left"][0]["settings"]["heading"] == "Left"
    assert zones["right"][0]["settings"]["heading"] == "Right"


# ---------------------------------------------------------------------------
# Manual save endpoint (drag-and-drop write path, bypasses Gemini)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_save_page_schema_endpoint_persists_sections(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    payload = {
        "page_key": "manual-save-test",
        "page_type": "static_page",
        "sections": [{"type": "text_block", "settings": {"heading": "Manually placed"}}],
    }
    put_resp = await async_client.put(
        "/api/v1/admin/store/tenant-a/ai/page-schema", json=payload, headers=headers
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["sections"][0]["settings"]["heading"] == "Manually placed"

    get_resp = await async_client.get(
        "/api/v1/admin/store/tenant-a/ai/page-schema?page_key=manual-save-test&page_type=static_page",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["sections"][0]["settings"]["heading"] == "Manually placed"


@pytest.mark.asyncio
async def test_manual_save_page_schema_scoped_to_authenticated_tenant(async_client: AsyncClient, seed_tokens):
    headers_a = {"Authorization": seed_tokens["tenant_admin_a"]}
    headers_b = {"Authorization": seed_tokens["tenant_admin_b"]}
    payload = {
        "page_key": "manual-save-scope",
        "page_type": "static_page",
        "sections": [{"type": "text_block", "settings": {"heading": "Tenant A only"}}],
    }
    # tenant-b's own admin can't write into tenant-a's store, even at the same page_key.
    cross_tenant_resp = await async_client.put(
        "/api/v1/admin/store/tenant-b/ai/page-schema",
        json={**payload, "sections": payload["sections"]},
        headers=headers_a,
    )
    assert cross_tenant_resp.status_code == 403

    own_resp = await async_client.put(
        "/api/v1/admin/store/tenant-a/ai/page-schema", json=payload, headers=headers_a
    )
    assert own_resp.status_code == 200


@pytest.mark.asyncio
async def test_customer_cannot_manually_save_page_schema(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {
        "page_key": "manual-save-customer",
        "page_type": "static_page",
        "sections": [{"type": "text_block", "settings": {"heading": "Nope"}}],
    }
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/ai/page-schema", json=payload, headers=headers
    )
    assert response.status_code == 403
