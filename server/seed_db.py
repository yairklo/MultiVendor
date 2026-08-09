import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.tenant import Tenant, SubscriptionPlan, TenantSettings
from app.core.security import get_password_hash

async def seed():
    async with AsyncSessionLocal() as session:
        # Create default plan
        plan = SubscriptionPlan(
            code="premium",
            name="Premium Plan",
            price_monthly=99.00,
            max_products=1000
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)

        # Create Tenant
        tenant = Tenant(
            slug="test-tenant",
            name="Test Store",
            plan_id=plan.id,
            status="active"
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        # Tenant settings
        settings = TenantSettings(
            tenant_id=tenant.id,
            currency="ILS",
            primary_color="#3b82f6",
            default_language="en"
        )
        session.add(settings)

        # Create Super Admin
        super_admin = User(
            email="super@multivendor.com",
            password_hash=get_password_hash("superadmin123"),
            full_name="Super Administrator",
            role="super_admin",
            is_active=True
        )
        session.add(super_admin)

        # Create Tenant Admin
        tenant_admin = User(
            email="admin@test-tenant.com",
            password_hash=get_password_hash("admin123"),
            full_name="Store Manager",
            role="tenant_admin",
            tenant_id=tenant.id,
            is_active=True
        )
        session.add(tenant_admin)

        # Create Customer
        customer = User(
            email="customer@gmail.com",
            password_hash=get_password_hash("customer123"),
            full_name="John Doe",
            role="customer",
            tenant_id=tenant.id,
            is_active=True
        )
        session.add(customer)

        await session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
