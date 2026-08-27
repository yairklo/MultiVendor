import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.user import User, UserStoreMembership
from app.models.tenant import Tenant, SubscriptionPlan, TenantSettings
from app.models.catalog import Product, ProductImage, ProductVariant
from app.core.security import get_password_hash

# Convenience dev-DB seed (targets whatever DATABASE_URL is configured, i.e.
# multivendor_dev by default) -- complements db/seed.sql, which is the
# fixture data the test suite truncates/reloads before every test against
# multivendor_test. Re-runnable: wipes and recreates the same rows each time.
DEMO_PASSWORD = "password"

async def seed():
    async with AsyncSessionLocal() as session:
        await _wipe(session)

        free_plan = SubscriptionPlan(code="free", name="Free Plan", price_monthly=0.00, max_products=50, max_storage_mb=500)
        pro_plan = SubscriptionPlan(code="pro", name="Pro Plan", price_monthly=29.99, max_products=1000, max_storage_mb=5000)
        session.add_all([free_plan, pro_plan])
        await session.flush()

        # Store 1 opts its whole catalog into the marketplace; Store 2 opts in
        # per-product instead -- the two ways to become marketplace-visible.
        store1 = Tenant(slug="store1", name="Store One", plan_id=free_plan.id, status="active", show_all_products_in_marketplace=True)
        store2 = Tenant(slug="store2", name="Store Two", plan_id=pro_plan.id, status="active", show_all_products_in_marketplace=False)
        session.add_all([store1, store2])
        await session.flush()

        session.add_all([
            TenantSettings(tenant_id=store1.id, currency="ILS", primary_color="#3b82f6", default_language="en"),
            TenantSettings(tenant_id=store2.id, currency="ILS", primary_color="#16a34a", default_language="en"),
        ])

        super_admin = User(
            email="superadmin@platform.com", password_hash=get_password_hash(DEMO_PASSWORD),
            full_name="Platform Super Admin", role="super_admin", is_active=True,
        )
        admin_store1 = User(
            email="admin.store1@platform.com", password_hash=get_password_hash(DEMO_PASSWORD),
            full_name="Store 1 Admin", role="user", is_active=True,
        )
        admin_store2 = User(
            email="admin.store2@platform.com", password_hash=get_password_hash(DEMO_PASSWORD),
            full_name="Store 2 Admin", role="user", is_active=True,
        )
        # The headline demo of global identity: one login, member of both stores.
        customer = User(
            email="customer@gmail.com", password_hash=get_password_hash(DEMO_PASSWORD),
            full_name="Global Customer", role="user", is_active=True,
        )
        session.add_all([super_admin, admin_store1, admin_store2, customer])
        await session.flush()

        session.add_all([
            UserStoreMembership(user_id=admin_store1.id, tenant_id=store1.id, role="tenant_admin"),
            UserStoreMembership(user_id=admin_store2.id, tenant_id=store2.id, role="tenant_admin"),
            UserStoreMembership(user_id=customer.id, tenant_id=store1.id, role="customer"),
            UserStoreMembership(user_id=customer.id, tenant_id=store2.id, role="customer"),
        ])

        product1 = Product(
            tenant_id=store1.id, name={"en": "Demo T-Shirt", "he": "חולצת דמו"}, slug="demo-tshirt",
            base_price=25.00, is_active=True, show_in_marketplace=True,
        )
        product2 = Product(
            tenant_id=store2.id, name={"en": "Demo Mug", "he": "ספל דמו"}, slug="demo-mug",
            base_price=15.00, is_active=True, show_in_marketplace=True,
        )
        session.add_all([product1, product2])
        await session.flush()

        session.add_all([
            ProductVariant(tenant_id=store1.id, product_id=product1.id, sku="TSHIRT-DEMO-1", stock_quantity=50),
            ProductVariant(tenant_id=store2.id, product_id=product2.id, sku="MUG-DEMO-1", stock_quantity=50),
            ProductImage(
                tenant_id=store1.id, product_id=product1.id,
                image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800&h=800&q=80",
                is_primary=True, sort_order=0,
            ),
            ProductImage(
                tenant_id=store2.id, product_id=product2.id,
                image_url="https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=800&h=800&q=80",
                is_primary=True, sort_order=0,
            ),
        ])

        await session.commit()
        print("Database seeded. Demo accounts (password for all: 'password'):")
        print("  superadmin@platform.com    - super admin")
        print("  admin.store1@platform.com  - tenant_admin of 'store1'")
        print("  admin.store2@platform.com  - tenant_admin of 'store2'")
        print("  customer@gmail.com         - global customer, member of both stores")

async def _wipe(session: AsyncSession):
    await session.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    for table in [
        "order_items", "orders", "master_orders", "marketplace_cart_items", "cart_items", "carts",
        "coupons", "product_reviews", "product_images", "product_variants", "products", "categories",
        "user_store_memberships", "users", "tenant_billing_logs", "tenant_settings", "tenants",
        "subscription_plans",
    ]:
        await session.execute(text(f"TRUNCATE TABLE {table}"))
    await session.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    await session.commit()

if __name__ == "__main__":
    asyncio.run(seed())
