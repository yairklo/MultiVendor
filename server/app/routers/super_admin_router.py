from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import get_super_admin
from app.models.tenant import SubscriptionPlan, Tenant
from app.models.user import User
from app.services.store_page_service import list_all_storefront_templates_service
from app.services.storefront_templates import (
    create_storefront_template,
    patch_storefront_template,
    template_row_to_admin_dict,
    update_storefront_template,
)
from app.services.super_admin_service import (
    create_tenant_admin,
    get_overview,
    list_audit_logs_admin,
    list_orders_admin,
    list_plans_admin,
    list_tenants_admin,
    list_users_admin,
    load_tenant,
    product_counts_by_tenant,
    tenant_admin_dict,
    write_audit,
)

super_admin_router = APIRouter(prefix="/api/v1/super-admin", tags=["Super Admin"])


class TenantSubscriptionUpdate(BaseModel):
    plan_id: int


class TenantMarketplaceUpdate(BaseModel):
    show_all_products_in_marketplace: bool


class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9-]+$")
    plan_id: int
    admin_email: EmailStr
    admin_full_name: str = Field(..., min_length=1, max_length=255)
    admin_password: Optional[str] = Field(None, min_length=8)
    show_all_products_in_marketplace: bool = False


class UserStatusUpdate(BaseModel):
    is_active: bool


class SimpleTenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    plan_id: int

    model_config = {"from_attributes": True}


class TenantAdminResponse(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    plan_id: int
    plan_code: str
    plan_name: str
    max_products: int
    product_count: int
    custom_domain: Optional[str] = None
    show_all_products_in_marketplace: bool
    stripe_connected: bool
    created_at: Optional[datetime] = None


class TenantListResponse(BaseModel):
    data: List[TenantAdminResponse]


class AuditLogItem(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    resource: str
    ip_address: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class AuditLogsResponse(BaseModel):
    data: List[AuditLogItem]


class PlatformOrderResponse(BaseModel):
    id: int
    order_number: str
    tenant_id: int
    tenant_name: str
    tenant_slug: str
    status: str
    total_amount: float
    platform_commission: float
    vendor_net_payout: float
    created_at: Optional[datetime] = None


class PlatformOrdersResponse(BaseModel):
    data: List[PlatformOrderResponse]


class PlanAdminResponse(BaseModel):
    id: int
    code: str
    name: str
    price_monthly: float
    max_products: int
    max_storage_mb: int
    features_json: Dict[str, Any]
    tenant_count: int


class PlansListResponse(BaseModel):
    data: List[PlanAdminResponse]


class UserMembershipResponse(BaseModel):
    tenant_id: int
    tenant_name: str
    tenant_slug: str
    role: str
    is_active: bool


class UserAdminResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    memberships: List[UserMembershipResponse]


class UsersListResponse(BaseModel):
    data: List[UserAdminResponse]


class OverviewResponse(BaseModel):
    tenants_total: int
    tenants_active: int
    tenants_suspended: int
    tenants_cancelled: int
    users_total: int
    products_total: int
    orders_total: int
    gmv: float
    platform_commission: float
    marketplace_vendors: int
    stripe_connected: int
    templates_active: int
    recent_tenants: List[TenantAdminResponse]
    recent_orders: List[PlatformOrderResponse]


class SuperAdminMeResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


@super_admin_router.get("/me", response_model=SuperAdminMeResponse)
async def get_admin_profile(admin: User = Depends(get_super_admin)):
    return SuperAdminMeResponse(
        id=admin.id,
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role,
    )


@super_admin_router.get("/overview", response_model=OverviewResponse)
async def get_platform_overview(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return await get_overview(db)


@super_admin_router.get("/tenants", response_model=TenantListResponse)
async def get_tenants(
    status: Optional[Literal["active", "suspended", "cancelled"]] = Query(None),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return TenantListResponse(data=await list_tenants_admin(db, status_filter=status, q=q))


@super_admin_router.post(
    "/tenants",
    response_model=TenantAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant(
    req: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return await create_tenant_admin(
        db,
        name=req.name,
        slug=req.slug,
        plan_id=req.plan_id,
        admin_email=req.admin_email,
        admin_full_name=req.admin_full_name,
        admin_password=req.admin_password,
        show_all_products_in_marketplace=req.show_all_products_in_marketplace,
        actor=admin,
    )


@super_admin_router.patch("/tenants/{tenant_id}/status", response_model=SimpleTenantResponse)
async def update_tenant_status(
    tenant_id: int,
    status: Literal["active", "suspended", "cancelled"],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    previous = tenant.status
    tenant.status = status
    await write_audit(
        db,
        admin,
        action="tenant.status",
        resource=f"tenant:{tenant.id}",
        details={"from": previous, "to": status},
        tenant_id=tenant.id,
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant


@super_admin_router.post("/tenants/{tenant_id}/subscription", response_model=SimpleTenantResponse)
async def update_tenant_subscription(
    tenant_id: int,
    req: TenantSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == req.plan_id))
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    previous = tenant.plan_id
    tenant.plan_id = req.plan_id
    await write_audit(
        db,
        admin,
        action="tenant.subscription",
        resource=f"tenant:{tenant.id}",
        details={"from": previous, "to": req.plan_id},
        tenant_id=tenant.id,
    )
    await db.commit()
    await db.refresh(tenant)
    return tenant


@super_admin_router.patch("/tenants/{tenant_id}/marketplace", response_model=TenantAdminResponse)
async def update_tenant_marketplace(
    tenant_id: int,
    req: TenantMarketplaceUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    tenant = await load_tenant(db, tenant_id)
    previous = bool(tenant.show_all_products_in_marketplace)
    tenant.show_all_products_in_marketplace = req.show_all_products_in_marketplace
    await write_audit(
        db,
        admin,
        action="tenant.marketplace",
        resource=f"tenant:{tenant.id}",
        details={"from": previous, "to": req.show_all_products_in_marketplace},
        tenant_id=tenant.id,
    )
    await db.commit()
    await db.refresh(tenant)
    counts = await product_counts_by_tenant(db)
    tenant = await load_tenant(db, tenant_id)
    return tenant_admin_dict(tenant, counts.get(tenant.id, 0))


@super_admin_router.get("/plans", response_model=PlansListResponse)
async def list_plans(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return PlansListResponse(data=await list_plans_admin(db))


@super_admin_router.get("/users", response_model=UsersListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return UsersListResponse(data=await list_users_admin(db))


@super_admin_router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
async def update_user_status(
    user_id: int,
    req: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "super_admin":
        raise HTTPException(status_code=400, detail="Cannot change super-admin status")

    previous = bool(user.is_active)
    user.is_active = req.is_active
    await write_audit(
        db,
        admin,
        action="user.status",
        resource=f"user:{user.id}",
        details={"from": previous, "to": req.is_active, "email": user.email},
    )
    await db.commit()
    users = await list_users_admin(db)
    updated = next((u for u in users if u["id"] == user.id), None)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@super_admin_router.get("/orders", response_model=PlatformOrdersResponse)
async def list_platform_orders(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return PlatformOrdersResponse(data=await list_orders_admin(db))


@super_admin_router.get("/audit-logs", response_model=AuditLogsResponse)
async def get_audit_logs(
    tenant_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    return AuditLogsResponse(data=await list_audit_logs_admin(db, tenant_id=tenant_id))


class StorefrontTemplateAdminResponse(BaseModel):
    id: int
    template_key: str
    name: str
    tagline: str
    swatch_json: Dict[str, Any]
    pages_json: Dict[str, Any]
    display_order: int
    is_active: bool
    is_builtin: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class StorefrontTemplateListResponse(BaseModel):
    data: List[StorefrontTemplateAdminResponse]


class StorefrontTemplateCreateRequest(BaseModel):
    template_key: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(..., min_length=1, max_length=100)
    tagline: str = Field(..., min_length=1, max_length=255)
    swatch_json: Dict[str, Any]
    pages_json: Dict[str, Any]
    display_order: int = 0


class StorefrontTemplateUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    tagline: str = Field(..., min_length=1, max_length=255)
    swatch_json: Dict[str, Any]
    pages_json: Dict[str, Any]
    display_order: Optional[int] = None


class StorefrontTemplatePatchRequest(BaseModel):
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.is_active is None and self.display_order is None:
            raise ValueError("Provide is_active and/or display_order")
        return self


@super_admin_router.get("/storefront-templates", response_model=StorefrontTemplateListResponse)
async def list_storefront_templates_admin(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    rows = await list_all_storefront_templates_service(db)
    return StorefrontTemplateListResponse(data=[template_row_to_admin_dict(r) for r in rows])


@super_admin_router.post(
    "/storefront-templates",
    response_model=StorefrontTemplateAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_storefront_template_admin(
    req: StorefrontTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    row = await create_storefront_template(
        template_key=req.template_key,
        name=req.name,
        tagline=req.tagline,
        swatch_json=req.swatch_json,
        pages_json=req.pages_json,
        display_order=req.display_order,
        db=db,
    )
    return template_row_to_admin_dict(row)


@super_admin_router.put("/storefront-templates/{template_key}", response_model=StorefrontTemplateAdminResponse)
async def update_storefront_template_admin(
    template_key: str,
    req: StorefrontTemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    row = await update_storefront_template(
        template_key,
        name=req.name,
        tagline=req.tagline,
        swatch_json=req.swatch_json,
        pages_json=req.pages_json,
        display_order=req.display_order,
        db=db,
    )
    return template_row_to_admin_dict(row)


@super_admin_router.patch("/storefront-templates/{template_key}", response_model=StorefrontTemplateAdminResponse)
async def patch_storefront_template_admin(
    template_key: str,
    req: StorefrontTemplatePatchRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_super_admin),
):
    row = await patch_storefront_template(
        template_key,
        is_active=req.is_active,
        display_order=req.display_order,
        db=db,
    )
    return template_row_to_admin_dict(row)
