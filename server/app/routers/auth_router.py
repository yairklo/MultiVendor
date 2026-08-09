from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.tenant_schemas import TenantRegisterRequest
from app.schemas.auth_schemas import TokenResponse, LoginRequest, CustomerRegisterRequest, UserResponse
from app.services.auth_service import register_tenant_service, login_service, register_customer_service

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Onboarding"])

@auth_router.post(
    "/register-tenant", 
    response_model=TokenResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a New Tenant Business",
    description="Registers a new business on the platform. This creates the Tenant entity and the initial Tenant Admin user. Returns a JWT access token for immediate login.",
    responses={
        201: {"description": "Tenant successfully registered."},
        400: {"description": "Tenant slug or email already exists."},
        422: {"description": "Validation error in request payload."}
    }
)
async def register_tenant(req: TenantRegisterRequest, bg_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return await register_tenant_service(req, db)

@auth_router.post(
    "/login", 
    response_model=TokenResponse, 
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates any user type (Super Admin, Tenant Admin, or Customer). Generates an access token holding Row-Level Security claims (e.g. tenant_id) inside the JWT payload.",
    responses={
        200: {"description": "Successfully authenticated."},
        401: {"description": "Invalid email or password."}
    }
)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login_service(req, db)

@auth_router.post(
    "/register-customer/{tenant_slug}", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register a Customer",
    description="Registers a new customer account securely partitioned to the specified tenant store. Assures isolated Row-Level Security for consumer profiles.",
    responses={
        201: {"description": "Customer successfully registered."},
        400: {"description": "Email already exists within this tenant."},
        404: {"description": "Tenant store not found."}
    }
)
async def register_customer(tenant_slug: str, req: CustomerRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_customer_service(tenant_slug, req, db)
