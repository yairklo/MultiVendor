from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.coupon import Coupon
from app.schemas.order_schemas import CouponCreateRequest, CouponUpdateRequest, CouponResponse

async def _get_tenant_id(tenant_slug: str, db: AsyncSession) -> int:
    result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id

async def list_tenant_coupons_service(tenant_slug: str, db: AsyncSession) -> list[CouponResponse]:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(select(Coupon).where(Coupon.tenant_id == tenant_id).order_by(Coupon.id.desc()))
    return [CouponResponse.model_validate(c, from_attributes=True) for c in result.scalars().all()]

async def create_tenant_coupon_service(tenant_slug: str, req: CouponCreateRequest, db: AsyncSession) -> CouponResponse:
    tenant_id = await _get_tenant_id(tenant_slug, db)

    existing = await db.execute(
        select(Coupon).where(Coupon.tenant_id == tenant_id, Coupon.code == req.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A coupon with this code already exists")

    coupon = Coupon(
        tenant_id=tenant_id,
        code=req.code,
        discount_type=req.discount_type,
        discount_val=req.discount_val,
        min_order_amt=req.min_order_amt,
        usage_limit=req.usage_limit,
        used_count=0,
        valid_until=req.valid_until,
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return CouponResponse.model_validate(coupon, from_attributes=True)

async def delete_tenant_coupon_service(tenant_slug: str, coupon_id: int, db: AsyncSession) -> None:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id, Coupon.tenant_id == tenant_id)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    await db.delete(coupon)
    await db.commit()

async def update_coupon_service(tenant_slug: str, coupon_id: int, req: CouponUpdateRequest, db: AsyncSession) -> CouponResponse:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id, Coupon.tenant_id == tenant_id)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    updates = req.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != coupon.code:
        existing = await db.execute(
            select(Coupon).where(Coupon.tenant_id == tenant_id, Coupon.code == updates["code"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="A coupon with this code already exists")
    for field, value in updates.items():
        setattr(coupon, field, value)

    await db.commit()
    await db.refresh(coupon)
    return CouponResponse.model_validate(coupon, from_attributes=True)

async def toggle_coupon_status_service(tenant_slug: str, coupon_id: int, is_active: bool, db: AsyncSession) -> CouponResponse:
    tenant_id = await _get_tenant_id(tenant_slug, db)
    result = await db.execute(
        select(Coupon).where(Coupon.id == coupon_id, Coupon.tenant_id == tenant_id)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    coupon.is_active = is_active
    await db.commit()
    await db.refresh(coupon)
    return CouponResponse.model_validate(coupon, from_attributes=True)
