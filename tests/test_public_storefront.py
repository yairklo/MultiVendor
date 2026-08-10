import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_store_config(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/config")
    assert response.status_code == 200
    data = response.json()
    assert "primary_color" in data
    assert "currency" in data

@pytest.mark.asyncio
async def test_get_store_config_invalid_tenant(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/invalid-tenant/config")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_store_config_with_null_supported_languages(async_client: AsyncClient, db_session):
    # A settings row created before supported_languages was ever set (or via
    # a path that leaves it NULL) used to 500 the whole config endpoint,
    # since the response schema required a list.
    from app.models.tenant import TenantSettings

    db_session.add(TenantSettings(tenant_id=1, primary_color="#123456", currency="USD"))
    await db_session.commit()

    response = await async_client.get("/api/v1/store/tenant-a/config")
    assert response.status_code == 200
    data = response.json()
    assert data["supported_languages"] == ["he"]
    assert data["primary_color"] == "#123456"

@pytest.mark.asyncio
async def test_list_products_with_pagination_and_search(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products?page=1&page_size=10&q=test&category_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "meta" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 10
    assert "data" in data

@pytest.mark.asyncio
@pytest.mark.parametrize("page, page_size, expected_status", [
    (0, 10, 422), # page ge=1
    (-1, 10, 422), 
    (1, 0, 422),  # page_size ge=1
    (1, 500, 422) # page_size le=100
])
async def test_list_products_pagination_boundaries(async_client: AsyncClient, page, page_size, expected_status):
    response = await async_client.get(f"/api/v1/store/tenant-a/products?page={page}&page_size={page_size}")
    assert response.status_code == expected_status

@pytest.mark.asyncio
async def test_inactive_products_hidden_from_public(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products")
    assert response.status_code == 200
    data = response.json()
    for product in data.get("data", []):
        assert product["is_active"] is True

@pytest.mark.asyncio
async def test_get_product_details_with_variants_and_images(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products/product-a1")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "product-a1"
    assert "variants" in data
    assert "images" in data

@pytest.mark.asyncio
async def test_list_product_reviews_only_returns_approved(async_client: AsyncClient, db_session):
    # Seeded review #1 on product-a1 is unapproved (is_approved=0) — the
    # storefront must never show it. Add an approved one and confirm only
    # that one comes back.
    from app.models.catalog import ProductReview

    db_session.add(ProductReview(
        tenant_id=1, product_id=1, user_id=4, rating=4, comment="Approved review",
        is_approved=True, is_verified_buyer=True
    ))
    await db_session.commit()

    response = await async_client.get("/api/v1/store/tenant-a/products/product-a1/reviews")
    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) == 1
    assert reviews[0]["comment"] == "Approved review"
    assert reviews[0]["customer_name"] == "Customer A"

async def _delete_seeded_review(db_session):
    # Seed data already includes review #1 (user 4 on product 1) — clear it
    # so these tests can exercise a fresh "first review from this customer"
    # scenario without tripping the one-review-per-product rule.
    from sqlalchemy import delete
    from app.models.catalog import ProductReview
    await db_session.execute(delete(ProductReview).where(ProductReview.id == 1))
    await db_session.commit()

@pytest.mark.asyncio
async def test_create_product_review_auto_approved_by_default(async_client: AsyncClient, seed_tokens, db_session):
    await _delete_seeded_review(db_session)
    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {"product_id": 1, "rating": 5, "comment": "Loved it"}
    response = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["is_approved"] is True
    assert body["rating"] == 5

    list_resp = await async_client.get("/api/v1/store/tenant-a/products/product-a1/reviews")
    assert any(r["comment"] == "Loved it" for r in list_resp.json())

@pytest.mark.asyncio
async def test_create_product_review_requires_authentication(async_client: AsyncClient):
    payload = {"product_id": 1, "rating": 5, "comment": "Nice"}
    response = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_product_review_duplicate_rejected(async_client: AsyncClient, seed_tokens, db_session):
    await _delete_seeded_review(db_session)
    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {"product_id": 1, "rating": 5, "comment": "First"}
    first = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload, headers=headers)
    assert first.status_code == 201

    second = await async_client.post(
        "/api/v1/store/tenant-a/reviews",
        json={"product_id": 1, "rating": 3, "comment": "Second"},
        headers=headers
    )
    assert second.status_code == 400

@pytest.mark.asyncio
async def test_create_product_review_marks_verified_buyer(async_client: AsyncClient, seed_tokens, db_session):
    from app.models.order import Order, OrderItem

    await _delete_seeded_review(db_session)
    order = Order(
        tenant_id=1, user_id=4, order_number="ORD-VERIFIED", subtotal=10, total_amount=10, status="completed"
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(OrderItem(
        tenant_id=1, order_id=order.id, variant_id=1, product_name="Product A1",
        sku="SKU-A1-1", unit_price=10, quantity=1
    ))
    await db_session.commit()

    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {"product_id": 1, "rating": 5, "comment": "Definitely bought this"}
    response = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["is_verified_buyer"] is True

@pytest.mark.asyncio
async def test_create_product_review_not_verified_without_purchase(async_client: AsyncClient, seed_tokens, db_session):
    await _delete_seeded_review(db_session)
    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {"product_id": 1, "rating": 5, "comment": "Heard good things"}
    response = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["is_verified_buyer"] is False

@pytest.mark.asyncio
async def test_create_product_review_pending_when_moderation_enabled(async_client: AsyncClient, seed_tokens, db_session):
    from app.models.tenant import TenantSettings

    await _delete_seeded_review(db_session)
    db_session.add(TenantSettings(tenant_id=1, review_moderation_enabled=True))
    await db_session.commit()

    headers = {"Authorization": seed_tokens["customer_a"]}
    payload = {"product_id": 1, "rating": 5, "comment": "Awaiting moderation"}
    response = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["is_approved"] is False

    list_resp = await async_client.get("/api/v1/store/tenant-a/products/product-a1/reviews")
    assert not any(r["comment"] == "Awaiting moderation" for r in list_resp.json())

@pytest.mark.asyncio
async def test_list_public_categories(async_client: AsyncClient, db_session):
    from app.models.catalog import Category

    db_session.add_all([
        Category(tenant_id=1, name={"en": "Electronics", "he": "אלקטרוניקה"}, slug="electronics"),
        Category(tenant_id=2, name={"en": "Other Tenant Category"}, slug="other-tenant-cat"),
    ])
    await db_session.commit()

    response = await async_client.get("/api/v1/store/tenant-a/categories")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) == 1
    assert categories[0]["slug"] == "electronics"

@pytest.mark.asyncio
async def test_search_query_actually_filters_products(async_client: AsyncClient, db_session):
    # q was previously accepted by the endpoint but silently ignored.
    from app.models.catalog import Product

    db_session.add(Product(
        tenant_id=1, name={"en": "Wireless Mouse", "he": "עכבר אלחוטי"}, slug="wireless-mouse",
        base_price=25.00, is_active=True
    ))
    await db_session.commit()

    response = await async_client.get("/api/v1/store/tenant-a/products?q=mouse")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["slug"] == "wireless-mouse"

@pytest.mark.asyncio
async def test_search_query_is_case_insensitive_and_matches_no_results(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products?q=PRODUCT")
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1

    response = await async_client.get("/api/v1/store/tenant-a/products?q=zzz_no_such_product")
    assert response.status_code == 200
    assert response.json()["data"] == []

@pytest.mark.asyncio
async def test_product_list_and_detail_include_average_rating(async_client: AsyncClient, db_session):
    from app.models.catalog import ProductReview

    db_session.add_all([
        ProductReview(tenant_id=1, product_id=1, user_id=4, rating=5, is_approved=True),
        ProductReview(tenant_id=1, product_id=1, user_id=5, rating=3, is_approved=True),
        # Unapproved reviews must not skew the average.
        ProductReview(tenant_id=1, product_id=1, user_id=4, rating=1, is_approved=False),
    ])
    await db_session.commit()

    list_resp = await async_client.get("/api/v1/store/tenant-a/products")
    product = next(p for p in list_resp.json()["data"] if p["slug"] == "product-a1")
    assert product["average_rating"] == 4.0
    assert product["review_count"] == 2

    detail_resp = await async_client.get("/api/v1/store/tenant-a/products/product-a1")
    assert detail_resp.json()["average_rating"] == 4.0
    assert detail_resp.json()["review_count"] == 2

@pytest.mark.asyncio
async def test_product_with_no_reviews_has_null_average_rating(async_client: AsyncClient):
    response = await async_client.get("/api/v1/store/tenant-a/products/product-a1")
    assert response.status_code == 200
    assert response.json()["average_rating"] is None
    assert response.json()["review_count"] == 0

@pytest.mark.asyncio
async def test_create_product_review_is_tenant_isolated(async_client: AsyncClient, seed_tokens):
    # customer_b belongs to tenant-b and must not be able to review a
    # tenant-a product through tenant-a's store path.
    headers_b = {"Authorization": seed_tokens["customer_b"]}
    payload = {"product_id": 1, "rating": 5, "comment": "Shouldn't work"}
    response = await async_client.post("/api/v1/store/tenant-a/reviews", json=payload, headers=headers_b)
    assert response.status_code == 403
