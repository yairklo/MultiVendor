from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.tenant import Tenant, TenantSettings
from app.schemas.tenant_schemas import TenantSettingsSchema

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

    await db.commit()
    await db.refresh(settings)

    return TenantSettingsSchema(
        primary_color=settings.primary_color,
        currency=settings.currency,
        logo_url=settings.logo_url,
        banner_url=settings.banner_url,
        custom_css=settings.custom_css,
        support_email=settings.support_email
    )
