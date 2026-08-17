from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User, UserStoreMembership
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

    # 4. Identity is global now: the admin's email must be free platform-wide,
    # not just within this new tenant.
    user_result = await db.execute(select(User).where(User.email == req.admin_email))
    if user_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=req.admin_email,
        password_hash=get_password_hash(req.admin_password),
        full_name=req.admin_full_name,
        role=UserRole.USER,
        is_active=True
    )
    db.add(user)
    await db.flush()

    membership = UserStoreMembership(user_id=user.id, tenant_id=tenant.id, role='tenant_admin')
    db.add(membership)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.id, is_super_admin=False)

    return TokenResponse(
        access_token=token,
        refresh_token=token,
        user_id=user.id,
        role=user.role,
    )

async def login_service(req: LoginRequest, db: AsyncSession) -> TokenResponse:
    # Identity is global: one row per email regardless of which store(s) the
    # user shops at or administers. req.tenant_slug is accepted for backwards
    # compatibility with older clients but no longer affects the lookup --
    # store-level authorization is re-checked per request (see deps.py), not
    # decided at login time.
    user_result = await db.execute(select(User).where(User.email == req.email))
    user = user_result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=user.id, is_super_admin=(user.role == UserRole.SUPER_ADMIN))

    return TokenResponse(
        access_token=token,
        refresh_token=token,
        user_id=user.id,
        role=user.role,
    )

async def register_customer_service(tenant_slug: str, req: CustomerRegisterRequest, db: AsyncSession) -> User:
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    user_result = await db.execute(select(User).where(User.email == req.email))
    if user_result.scalar_one_or_none():
        # A global account already owns this email -- direct them to log in
        # instead (logging in auto-joins any store they then shop at, see
        # deps.get_tenant_customer), rather than silently taking over the
        # existing account or creating a duplicate.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered. Please log in instead.")

    user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        full_name=req.full_name,
        role=UserRole.USER,
        is_active=True
    )
    db.add(user)
    await db.flush()

    membership = UserStoreMembership(user_id=user.id, tenant_id=tenant.id, role='customer')
    db.add(membership)

    await db.commit()
    await db.refresh(user)
    return user
