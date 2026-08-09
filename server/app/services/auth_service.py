from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.tenant import Tenant, SubscriptionPlan
from app.schemas.tenant_schemas import TenantRegisterRequest
from app.schemas.auth_schemas import LoginRequest, CustomerRegisterRequest, TokenResponse, UserResponse
from app.schemas.common_schemas import UserRole
from app.core.security import get_password_hash, verify_password, create_access_token

async def register_tenant_service(req: TenantRegisterRequest, db: AsyncSession) -> TokenResponse:
    # 1. Check if slug exists
    result = await db.execute(select(Tenant).where(Tenant.slug == req.store_slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")
    
    # 2. Get Plan
    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == req.plan_code))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")
        
    # 3. Create Tenant
    tenant = Tenant(
        name=req.store_name,
        slug=req.store_slug,
        plan_id=plan.id,
        status='active'
    )
    db.add(tenant)
    await db.flush()
    
    # 4. Check if admin email exists globally for tenants (or just globally)
    # Actually email uniqueness per tenant is required, for tenant_admin it's tenant_id
    user_result = await db.execute(select(User).where(User.email == req.admin_email, User.tenant_id == tenant.id))
    if user_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        
    user = User(
        tenant_id=tenant.id,
        email=req.admin_email,
        password_hash=get_password_hash(req.admin_password),
        full_name=req.admin_full_name,
        role=UserRole.TENANT_ADMIN,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token(subject=user.id, role=user.role, tenant_slug=tenant.slug)
    
    return TokenResponse(
        access_token=token,
        refresh_token=token,
        user_id=user.id,
        role=user.role,
        tenant_id=tenant.id
    )

async def login_service(req: LoginRequest, db: AsyncSession) -> TokenResponse:
    if req.tenant_slug:
        # Tenant user or admin
        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == req.tenant_slug))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        user_result = await db.execute(select(User).where(User.email == req.email, User.tenant_id == tenant.id))
        user = user_result.scalar_one_or_none()
    else:
        # Super admin
        user_result = await db.execute(select(User).where(User.email == req.email, User.tenant_id.is_(None)))
        user = user_result.scalar_one_or_none()
        tenant = None

    if not user or not verify_password(req.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
    token = create_access_token(subject=user.id, role=user.role, tenant_slug=tenant.slug if tenant else None)
    
    return TokenResponse(
        access_token=token,
        refresh_token=token,
        user_id=user.id,
        role=user.role,
        tenant_id=tenant.id if tenant else None
    )

async def register_customer_service(tenant_slug: str, req: CustomerRegisterRequest, db: AsyncSession) -> User:
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        
    user_result = await db.execute(select(User).where(User.email == req.email, User.tenant_id == tenant.id))
    if user_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        password_hash=get_password_hash(req.password),
        full_name=req.full_name,
        role=UserRole.CUSTOMER,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
