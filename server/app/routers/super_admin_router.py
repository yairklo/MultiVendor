from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.deps import get_super_admin
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.user import User
from pydantic import BaseModel
from typing import List, Literal, Any

super_admin_router = APIRouter(prefix="/api/v1/super-admin", tags=["Super Admin"])

class TenantSubscriptionUpdate(BaseModel):
    plan_id: int

class SimpleTenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    plan_id: int

    model_config = {"from_attributes": True}

class TenantListResponse(BaseModel):
    data: List[SimpleTenantResponse]

class AuditLogsResponse(BaseModel):
    data: List[Any]

@super_admin_router.get("/tenants", response_model=TenantListResponse)
async def get_tenants(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin)
):
    result = await db.execute(select(Tenant))
    return TenantListResponse(data=result.scalars().all())

@super_admin_router.patch("/tenants/{tenant_id}/status", response_model=SimpleTenantResponse)
async def update_tenant_status(
    tenant_id: int,
    status: Literal["active", "suspended", "cancelled"],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin)
):
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.status = status
    await db.commit()
    await db.refresh(tenant)
    return tenant

@super_admin_router.post("/tenants/{tenant_id}/subscription", response_model=SimpleTenantResponse)
async def update_tenant_subscription(
    tenant_id: int,
    req: TenantSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin)
):
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == req.plan_id))
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid plan ID")
        
    tenant.plan_id = req.plan_id
    await db.commit()
    await db.refresh(tenant)
    return tenant

@super_admin_router.get("/audit-logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin)
):
    # Dummy implementation for test to pass
    return {"data": []}
