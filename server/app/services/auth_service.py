from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from jose import JWTError, jwt
from app.models.user import User, UserStoreMembership
from app.models.tenant import Tenant, SubscriptionPlan, TenantSettings
from app.schemas.tenant_schemas import TenantRegisterRequest
from app.schemas.auth_schemas import LoginRequest, CustomerRegisterRequest, TokenResponse
from app.schemas.common_schemas import UserRole
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, refresh_token_ttl_seconds,
)
from app.core.config import settings
from app.db.session import redis_client
from app.db.tenant_context import unscoped

REFRESH_KEY_PREFIX = "refresh:"


async def _persist_refresh_jti(jti: str, user_id: int) -> None:
    await redis_client.set(f"{REFRESH_KEY_PREFIX}{jti}", str(user_id), ex=refresh_token_ttl_seconds())


async def _issue_token_pair(user: User, store_role: str | None = None) -> tuple[str, str]:
    access = create_access_token(
        subject=user.id,
        is_super_admin=(user.role == UserRole.SUPER_ADMIN),
        role=user.role,
        store_role=store_role,
    )
    refresh, jti = create_refresh_token(user.id)
    await _persist_refresh_jti(jti, user.id)
    return access, refresh


def _token_response(user: User, access: str, refresh: str, store_role: str | None = None) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        role=user.role,
        store_role=store_role,
    )


async def _lookup_store_role(user_id: int, tenant_slug: str | None, db: AsyncSession) -> str | None:
    if not tenant_slug:
        return None
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        return None
    membership_result = await db.execute(
        select(UserStoreMembership.role).where(
            UserStoreMembership.user_id == user_id,
            UserStoreMembership.tenant_id == tenant_id,
        )
    )
    return membership_result.scalar_one_or_none()


async def register_tenant_service(req: TenantRegisterRequest, db: AsyncSession) -> TokenResponse:
    result = await db.execute(select(Tenant).where(Tenant.slug == req.store_slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")

    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == req.plan_code))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan code")

    tenant = Tenant(
        name=req.store_name,
        slug=req.store_slug,
        plan_id=plan.id,
        status='active'
    )
    db.add(tenant)
    await db.flush()

    # New tenant has no bound tenant context yet (it's being created right
    # now, on the platform plane) -- explicit tenant_id + unscoped() satisfies
    # the session-level RLS guard (app/db/session.py's before_flush listener)
    # the same way seed/admin platform-plane operations do elsewhere.
    with unscoped():
        db.add(TenantSettings(tenant_id=tenant.id))
        await db.flush()

    user_result = await db.execute(select(User).where(User.email == req.admin_email))
    existing = user_result.scalar_one_or_none()

    if existing:
        if existing.role == UserRole.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        if not existing.is_active or not verify_password(req.admin_password, existing.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        user = existing
    else:
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

    access, refresh = await _issue_token_pair(user, store_role='tenant_admin')
    return _token_response(user, access, refresh, store_role='tenant_admin')


async def login_service(req: LoginRequest, db: AsyncSession) -> TokenResponse:
    user_result = await db.execute(select(User).where(User.email == req.email))
    user = user_result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    store_role = await _lookup_store_role(user.id, req.tenant_slug, db)
    access, refresh = await _issue_token_pair(user, store_role=store_role)
    return _token_response(user, access, refresh, store_role=store_role)


async def refresh_tokens_service(refresh_token: str, db: AsyncSession) -> TokenResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exception

    if payload.get("typ") != "refresh":
        raise credentials_exception
    user_id = payload.get("sub")
    jti = payload.get("jti")
    if user_id is None or not jti:
        raise credentials_exception

    stored = await redis_client.get(f"{REFRESH_KEY_PREFIX}{jti}")
    if stored is None or str(stored) != str(user_id):
        raise credentials_exception
    await redis_client.delete(f"{REFRESH_KEY_PREFIX}{jti}")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception

    access, refresh = await _issue_token_pair(user)
    return _token_response(user, access, refresh)


async def register_customer_global_service(req: CustomerRegisterRequest, db: AsyncSession) -> TokenResponse:
    # A marketplace-wide account: no UserStoreMembership row, since the
    # customer hasn't shopped at (or been scoped to) any one store yet --
    # login_service/_lookup_store_role already treats "no membership" as a
    # normal state (store_role=None), so this needs no special-casing there.
    user_result = await db.execute(select(User).where(User.email == req.email))
    if user_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered. Please log in instead.")

    user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        full_name=req.full_name,
        role=UserRole.USER,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access, refresh = await _issue_token_pair(user)
    return _token_response(user, access, refresh)


async def register_customer_service(tenant_slug: str, req: CustomerRegisterRequest, db: AsyncSession) -> User:
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    user_result = await db.execute(select(User).where(User.email == req.email))
    if user_result.scalar_one_or_none():
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
