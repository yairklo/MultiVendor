from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from app.models.tenant import Tenant, TenantSettings, SubscriptionPlan
from app.models.order import Order
from app.schemas.tenant_schemas import TenantSettingsSchema, TenantUpdateSchema, TenantResponse
from datetime import datetime, timezone
import json

async def update_tenant_service(tenant_slug: str, req: TenantUpdateSchema, db: AsyncSession) -> TenantResponse:
    tenant_result = await db.execute(
        select(Tenant)
        .options(joinedload(Tenant.plan), joinedload(Tenant.settings))
        .where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if req.custom_domain:
        tenant.custom_domain = req.custom_domain

    await db.commit()

    tenant_result = await db.execute(
        select(Tenant)
        .options(joinedload(Tenant.plan), joinedload(Tenant.settings))
        .where(Tenant.id == tenant.id)
    )
    tenant = tenant_result.scalar_one()

    tenant_data = {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "plan_code": tenant.plan.code if tenant.plan else "free",
        "status": tenant.status,
        "created_at": tenant.created_at,
        "custom_domain": tenant.custom_domain,
        "settings": TenantSettingsSchema.model_validate(tenant.settings) if tenant.settings else None
    }
    return TenantResponse(**tenant_data)


async def update_store_settings_service(tenant_slug: str, req: TenantSettingsSchema, db: AsyncSession) -> TenantSettingsSchema:
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    settings_result = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id))
    settings = settings_result.scalar_one_or_none()
    if not settings:
        settings = TenantSettings(tenant_id=tenant.id)
        db.add(settings)

    settings.primary_color = req.primary_color
    settings.currency = req.currency
    settings.logo_url = req.logo_url
    settings.banner_url = req.banner_url
    settings.custom_css = req.custom_css
    settings.support_email = req.support_email
    settings.supported_languages = req.supported_languages
    settings.default_language = req.default_language
    settings.review_moderation_enabled = req.review_moderation_enabled
    settings.allow_unverified_reviews = req.allow_unverified_reviews

    await db.commit()
    await db.refresh(settings)

    return TenantSettingsSchema.model_validate(settings)

async def upgrade_subscription_service(tenant_slug: str, target_plan_code: str, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == target_plan_code))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant.plan_id = plan.id
    await db.commit()

    return {
        "plan_code": plan.code,
        "max_products": plan.max_products,
        "max_storage_mb": plan.max_storage_mb
    }

async def get_current_subscription_service(tenant_slug: str, db: AsyncSession):
    tenant_result = await db.execute(
        select(Tenant).options(joinedload(Tenant.plan)).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return {
        "plan_code": tenant.plan.code,
        "max_products": tenant.plan.max_products,
        "max_storage_mb": tenant.plan.max_storage_mb
    }

async def get_tenant_analytics_service(tenant_slug: str, start_date: str, end_date: str, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    try:
        sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format, use ISO8601")

    # query total sales and order count
    query = (
        select(
            cast(Order.created_at, Date).label('date'),
            func.sum(Order.total_amount).label('total_sales'),
            func.count(Order.id).label('order_count')
        )
        .where(
            Order.tenant_id == tenant_id,
            Order.created_at >= sd,
            Order.created_at <= ed
        )
        .group_by(cast(Order.created_at, Date))
    )
    result = await db.execute(query)
    rows = result.all()
    
    data = []
    for row in rows:
        data.append({
            "date": row.date.isoformat() if row.date else None,
            "total_sales": float(row.total_sales) if row.total_sales else 0.0,
            "order_count": row.order_count
        })
        
    return {"data": data}
