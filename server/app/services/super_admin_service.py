from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, status
from pydantic import EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.security import get_password_hash
from app.db.tenant_context import unscoped
from app.models.catalog import Product
from app.models.order import Order
from app.models.storefront_template import StorefrontTemplate
from app.models.tenant import SubscriptionPlan, Tenant, TenantSettings
from app.models.user import AuditLog, User, UserStoreMembership


def _money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def tenant_admin_dict(tenant: Tenant, product_count: int = 0) -> dict[str, Any]:
    plan = tenant.plan
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "plan_id": tenant.plan_id,
        "plan_code": plan.code if plan else "",
        "plan_name": plan.name if plan else "",
        "max_products": plan.max_products if plan else 0,
        "product_count": product_count,
        "custom_domain": tenant.custom_domain,
        "show_all_products_in_marketplace": bool(tenant.show_all_products_in_marketplace),
        "stripe_connected": bool(tenant.stripe_account_id),
        "created_at": tenant.created_at,
    }


async def product_counts_by_tenant(db: AsyncSession) -> dict[int, int]:
    with unscoped():
        rows = (await db.execute(
            select(Product.tenant_id, func.count(Product.id)).group_by(Product.tenant_id)
        )).all()
    return {int(tenant_id): int(count) for tenant_id, count in rows}


async def load_tenant(db: AsyncSession, tenant_id: int) -> Tenant:
    result = await db.execute(
        select(Tenant).options(joinedload(Tenant.plan)).where(Tenant.id == tenant_id)
    )
    tenant = result.unique().scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


async def list_tenants_admin(
    db: AsyncSession,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
) -> list[dict[str, Any]]:
    counts = await product_counts_by_tenant(db)
    stmt = select(Tenant).options(joinedload(Tenant.plan)).order_by(Tenant.created_at.desc())
    if status_filter:
        stmt = stmt.where(Tenant.status == status_filter)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Tenant.name.ilike(like), Tenant.slug.ilike(like)))
    tenants = (await db.execute(stmt)).unique().scalars().all()
    return [tenant_admin_dict(t, counts.get(t.id, 0)) for t in tenants]


async def get_overview(db: AsyncSession) -> dict[str, Any]:
    tenants_total = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    tenants_active = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.status == "active")
    )).scalar() or 0
    tenants_suspended = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.status == "suspended")
    )).scalar() or 0
    tenants_cancelled = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.status == "cancelled")
    )).scalar() or 0
    users_total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    templates_active = (await db.execute(
        select(func.count(StorefrontTemplate.id)).where(StorefrontTemplate.is_active.is_(True))
    )).scalar() or 0
    marketplace_vendors = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.show_all_products_in_marketplace.is_(True))
    )).scalar() or 0
    stripe_connected = (await db.execute(
        select(func.count(Tenant.id)).where(Tenant.stripe_account_id.isnot(None))
    )).scalar() or 0

    with unscoped():
        products_total = (await db.execute(select(func.count(Product.id)))).scalar() or 0
        orders_total = (await db.execute(select(func.count(Order.id)))).scalar() or 0
        gmv = (await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.status.in_(("processing", "shipped", "completed"))
            )
        )).scalar()
        commission = (await db.execute(
            select(func.coalesce(func.sum(Order.platform_commission), 0))
        )).scalar()

    recent_tenants = await list_tenants_admin(db)
    recent_orders = await list_orders_admin(db, limit=8)

    return {
        "tenants_total": int(tenants_total),
        "tenants_active": int(tenants_active),
        "tenants_suspended": int(tenants_suspended),
        "tenants_cancelled": int(tenants_cancelled),
        "users_total": int(users_total),
        "products_total": int(products_total),
        "orders_total": int(orders_total),
        "gmv": _money(gmv),
        "platform_commission": _money(commission),
        "marketplace_vendors": int(marketplace_vendors),
        "stripe_connected": int(stripe_connected),
        "templates_active": int(templates_active),
        "recent_tenants": recent_tenants[:5],
        "recent_orders": recent_orders,
    }


async def list_plans_admin(db: AsyncSession) -> list[dict[str, Any]]:
    counts = {
        plan_id: int(count)
        for plan_id, count in (await db.execute(
            select(Tenant.plan_id, func.count(Tenant.id)).group_by(Tenant.plan_id)
        )).all()
    }
    plans = (await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.price_monthly))).scalars().all()
    return [
        {
            "id": plan.id,
            "code": plan.code,
            "name": plan.name,
            "price_monthly": _money(plan.price_monthly),
            "max_products": plan.max_products,
            "max_storage_mb": plan.max_storage_mb,
            "features_json": plan.features_json or {},
            "tenant_count": counts.get(plan.id, 0),
        }
        for plan in plans
    ]


async def list_users_admin(db: AsyncSession) -> list[dict[str, Any]]:
    users = (await db.execute(
        select(User)
        .options(selectinload(User.memberships).joinedload(UserStoreMembership.tenant))
        .order_by(User.created_at.desc())
    )).unique().scalars().all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": bool(user.is_active),
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "memberships": [
                {
                    "tenant_id": m.tenant_id,
                    "tenant_name": m.tenant.name if m.tenant else "",
                    "tenant_slug": m.tenant.slug if m.tenant else "",
                    "role": m.role,
                    "is_active": bool(m.is_active),
                }
                for m in user.memberships
            ],
        }
        for user in users
    ]


async def list_orders_admin(db: AsyncSession, limit: int = 100) -> list[dict[str, Any]]:
    with unscoped():
        rows = (await db.execute(
            select(Order, Tenant)
            .join(Tenant, Order.tenant_id == Tenant.id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )).all()
    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "tenant_slug": tenant.slug,
            "status": order.status,
            "total_amount": _money(order.total_amount),
            "platform_commission": _money(order.platform_commission),
            "vendor_net_payout": _money(order.vendor_net_payout),
            "created_at": order.created_at,
        }
        for order, tenant in rows
    ]


async def list_audit_logs_admin(
    db: AsyncSession,
    tenant_id: Optional[int] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": log.id,
            "tenant_id": log.tenant_id,
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "ip_address": log.ip_address,
            "details_json": log.details_json,
            "created_at": log.created_at,
        }
        for log in logs
    ]


async def write_audit(
    db: AsyncSession,
    admin: User,
    action: str,
    resource: str,
    details: Optional[dict[str, Any]] = None,
    tenant_id: Optional[int] = None,
) -> None:
    db.add(AuditLog(
        tenant_id=tenant_id,
        user_id=admin.id,
        action=action,
        resource=resource,
        details_json=details,
    ))


async def create_tenant_admin(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    plan_id: int,
    admin_email: EmailStr | str,
    admin_full_name: str,
    admin_password: Optional[str],
    show_all_products_in_marketplace: bool,
    actor: User,
) -> dict[str, Any]:
    existing = (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")

    plan = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan ID")

    tenant = Tenant(
        name=name,
        slug=slug,
        plan_id=plan.id,
        status="active",
        show_all_products_in_marketplace=show_all_products_in_marketplace,
    )
    db.add(tenant)
    await db.flush()

    with unscoped():
        db.add(TenantSettings(tenant_id=tenant.id))
        await db.flush()

    user = (await db.execute(select(User).where(User.email == str(admin_email)))).scalar_one_or_none()
    if user:
        if user.role == "super_admin":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    else:
        if not admin_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_password is required when creating a new store owner",
            )
        user = User(
            email=str(admin_email),
            password_hash=get_password_hash(admin_password),
            full_name=admin_full_name,
            role="user",
            is_active=True,
        )
        db.add(user)
        await db.flush()

    db.add(UserStoreMembership(user_id=user.id, tenant_id=tenant.id, role="tenant_admin"))
    await write_audit(
        db,
        actor,
        action="tenant.create",
        resource=f"tenant:{tenant.id}",
        details={"slug": slug, "plan_id": plan.id},
        tenant_id=tenant.id,
    )
    await db.commit()

    tenant = await load_tenant(db, tenant.id)
    return tenant_admin_dict(tenant, 0)
