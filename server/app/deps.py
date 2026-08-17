from fastapi import Depends, HTTPException, status
from typing import Optional
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.core.config import settings
from app.db.session import get_db, get_redis
from app.models.user import User, UserStoreMembership
from app.models.tenant import Tenant
from app.schemas.common_schemas import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

async def get_optional_user(token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)), db: AsyncSession = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.id == int(user_id)))
    return result.scalar_one_or_none()

async def get_current_tenant(tenant_slug: str, db: AsyncSession = Depends(get_db)) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant.status != 'active':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is suspended or cancelled")
    return tenant

def require_role(allowed_roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return current_user
    return role_checker

async def _get_membership(user_id: int, tenant_id: int, db: AsyncSession) -> Optional[UserStoreMembership]:
    result = await db.execute(
        select(UserStoreMembership).where(
            UserStoreMembership.user_id == user_id,
            UserStoreMembership.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()

async def get_tenant_admin(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Deliberately NOT auto-provisioned: unlike get_tenant_customer below, a
    # tenant_admin membership must already exist. Auto-granting admin on any
    # store a user happens to hit would be a privilege-escalation hole.
    membership = await _get_membership(current_user.id, tenant.id, db)
    if not membership or membership.role != 'tenant_admin' or not membership.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

async def get_tenant_customer(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> User:
    # A global user can shop at any active store without pre-registering
    # there first -- the first time they touch a tenant as a shopper (review,
    # checkout, ...) their 'customer' membership is created on demand. This is
    # what makes "one login, every store" actually work end to end; it does
    # NOT apply to tenant_admin (see get_tenant_admin) which is never
    # auto-granted.
    membership = await _get_membership(current_user.id, tenant.id, db)
    if not membership:
        membership = UserStoreMembership(user_id=current_user.id, tenant_id=tenant.id, role='customer')
        db.add(membership)
        await db.commit()
    elif not membership.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user

def get_super_admin(current_user: User = Depends(require_role([UserRole.SUPER_ADMIN]))) -> User:
    return current_user
