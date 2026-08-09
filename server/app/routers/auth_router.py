from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.tenant_schemas import TenantRegisterRequest
from app.schemas.auth_schemas import TokenResponse, LoginRequest, CustomerRegisterRequest, UserResponse
from app.services.auth_service import register_tenant_service, login_service, register_customer_service

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Auth & Onboarding"])

@auth_router.post("/register-tenant", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(req: TenantRegisterRequest, bg_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Registers a new tenant business + tenant_admin user."""
    return await register_tenant_service(req, db)

@auth_router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates SuperAdmin, TenantAdmin, or Customer."""
    return await login_service(req, db)

@auth_router.post("/register-customer/{tenant_slug}", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(tenant_slug: str, req: CustomerRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registers a customer under a specific tenant store."""
    return await register_customer_service(tenant_slug, req, db)
