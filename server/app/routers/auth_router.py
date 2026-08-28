from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.tenant_schemas import TenantRegisterRequest
from app.schemas.auth_schemas import (
    TokenResponse, LoginRequest, CustomerRegisterRequest, UserResponse, RefreshTokenRequest,
    PasswordResetRequest, PasswordResetConfirmRequest,
)
from app.services.auth_service import (
    register_tenant_service, login_service, register_customer_service, register_customer_global_service,
    refresh_tokens_service, request_password_reset_service, confirm_password_reset_service,
)
from fastapi import Request
from app.core.limiter import limiter

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
@limiter.limit("10/minute")
async def register_tenant(request: Request, req: TenantRegisterRequest, bg_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login_service(req, db)

@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate Refresh Token",
    description="Exchanges a valid refresh token for a new access token and a rotated refresh token. The previous refresh token is invalidated.",
)
@limiter.limit("10/minute")
async def refresh_tokens(request: Request, req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    return await refresh_tokens_service(req.refresh_token, db)

@auth_router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a Customer (marketplace-wide)",
    description="Registers a new customer account that is not scoped to any single store. Returns a JWT access token for immediate login, so the account can shop across every vendor on the marketplace.",
    responses={
        201: {"description": "Customer successfully registered."},
        409: {"description": "Email already registered."},
        422: {"description": "Validation error in request payload."}
    }
)
@limiter.limit("10/minute")
async def register_customer_global(request: Request, req: CustomerRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_customer_global_service(req, db)

@auth_router.post(
    "/password-reset/request",
    status_code=status.HTTP_200_OK,
    summary="Request a Password Reset",
    description="Sends a password-reset link to the given email if an active account owns it. Always returns the same generic response so the endpoint can't be used to enumerate registered emails.",
)
@limiter.limit("5/minute")
async def request_password_reset(request: Request, req: PasswordResetRequest, bg_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    await request_password_reset_service(req.email, bg_tasks, db)
    return {"detail": "If that email is registered, a password reset link has been sent."}

@auth_router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm a Password Reset",
    description="Sets a new password using a token from a password-reset email. The token is single-use and expires shortly after it's issued.",
    responses={
        400: {"description": "Reset token is missing, invalid, expired, or already used."},
        422: {"description": "Validation error in request payload."}
    }
)
@limiter.limit("10/minute")
async def confirm_password_reset(request: Request, req: PasswordResetConfirmRequest, db: AsyncSession = Depends(get_db)):
    await confirm_password_reset_service(req.token, req.new_password, db)
    return {"detail": "Password updated successfully."}

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
@limiter.limit("10/minute")
async def register_customer(request: Request, tenant_slug: str, req: CustomerRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_customer_service(tenant_slug, req, db)
