import pytest
from httpx import AsyncClient
from app.models.catalog import Product, ProductVariant, ProductBundleItem
from app.models.tenant import Tenant
from sqlalchemy import select

@pytest.mark.asyncio
async def test_v2_custom_domain_update(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    # Update domain
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/domain",
        headers=headers,
        json={"custom_domain": "shop.myteststore.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["custom_domain"] == "shop.myteststore.com"

@pytest.mark.asyncio
async def test_v2_store_settings_i18n(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.put(
        "/api/v1/admin/store/tenant-a/settings",
        headers=headers,
        json={
            "supported_languages": ["en", "he"],
            "default_language": "en",
            "review_moderation_enabled": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "en" in data["supported_languages"]
    assert data["review_moderation_enabled"] is True

@pytest.mark.asyncio
async def test_v2_product_i18n_missing_lang_422(async_client: AsyncClient, seed_tokens):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    response = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json={
            "name": {"en": "Only English Name"}, # Missing hebrew
            "slug": "missing-he",
            "base_price": 50.00,
            "variants": [{"sku": "SKU-HE", "price_override": 50.00, "stock_quantity": 10}],
            "images": ["http://test.com/img.png"]
        }
    )
    assert response.status_code == 422
    assert "Missing required translations" in response.text

@pytest.mark.asyncio
async def test_v2_digital_goods_checkout_bypasses_shipping(async_client: AsyncClient, seed_tokens, db_session):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    
    # Create digital product
    prod_resp = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json={
            "name": {"en": "Digital Ebook", "he": "ספר דיגיטלי"},
            "slug": "digital-ebook-v2",
            "base_price": 19.99,
            "product_type": "digital",
            "variants": [{"sku": "EBK-1-V2", "price_override": 19.99, "stock_quantity": 999}],
            "images": []
        }
    )
    assert prod_resp.status_code == 201
    prod_data = prod_resp.json()
    var_id = prod_data["variants"][0]["id"]
    
    # Customer logs in
    cust_headers = {"Authorization": seed_tokens["customer_a"]}
    
    cart_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # Add to cart
    add_resp = await async_client.post(
        f"/api/v1/store/tenant-a/cart/{cart_id}/items",
        headers=cust_headers,
        json={"variant_id": var_id, "quantity": 1}
    )
    assert add_resp.status_code == 200
    
    # Checkout without shipping_address
    checkout_resp = await async_client.post(
        "/api/v1/storefront/tenant-a/checkout",
        headers=cust_headers,
        json={
            "cart_id": cart_id,
            "payment_token": "987e6543-e21b-34d3-b456-426614174999",
            # NO SHIPPING ADDRESS
        }
    )
    assert checkout_resp.status_code == 200
    order_data = checkout_resp.json()
    assert order_data["order_type"] == "digital"

@pytest.mark.asyncio
async def test_v2_bundle_checkout_deducts_components(async_client: AsyncClient, seed_tokens, db_session):
    headers = {"Authorization": seed_tokens["tenant_admin_a"]}
    
    # 1. Create a base physical product
    base_prod = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json={
            "name": {"en": "Component A", "he": "רכיב א"},
            "slug": "comp-a-v2",
            "base_price": 10.0,
            "variants": [{"sku": "CA-1-V2", "stock_quantity": 10}],
            "images": []
        }
    )
    comp_var_id = base_prod.json()["variants"][0]["id"]
    
    # 2. Create Bundle product
    bundle_prod = await async_client.post(
        "/api/v1/admin/store/tenant-a/products",
        headers=headers,
        json={
            "name": {"en": "Bundle X", "he": "באנדל X"},
            "slug": "bundle-x-v2",
            "base_price": 15.0,
            "is_bundle": True,
            "bundle_items": [
                {"component_variant_id": comp_var_id, "quantity": 2}
            ],
            "variants": [{"sku": "BNDL-X-V2", "stock_quantity": 100}],
            "images": []
        }
    )
    bundle_var_id = bundle_prod.json()["variants"][0]["id"]
    
    # 3. Add to cart
    cust_headers = {"Authorization": seed_tokens["customer_a"]}
    
    cart_id = "660e8400-e29b-41d4-a716-446655440001"
    
    await async_client.post(
        f"/api/v1/store/tenant-a/cart/{cart_id}/items",
        headers=cust_headers,
        json={"variant_id": bundle_var_id, "quantity": 2} # Buying 2 bundles -> requires 4 components
    )
    
    # 4. Checkout
    checkout_resp = await async_client.post(
        "/api/v1/store/tenant-a/cart/checkout",
        headers=cust_headers,
        json={
            "cart_id": cart_id,
            "payment_token": "987e6543-e21b-34d3-b456-426614174999",
            "shipping_address": {"city": "Tel Aviv"}
        }
    )
    assert checkout_resp.status_code == 200
    
    # 5. Check component stock
    comp_var = await db_session.execute(select(ProductVariant).where(ProductVariant.id == comp_var_id))
    cv = comp_var.scalar_one()
    # Started with 10, deducted 2 * 2 = 4. Remaining: 6.
    assert cv.stock_quantity == 6
