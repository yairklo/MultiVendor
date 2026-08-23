from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from app.schemas.common_schemas import UserRole, PaginatedResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "owner@store.com",
            "password": "strongPassword123!",
            "tenant_slug": "nike-israel"
        }
    })

class RefreshTokenRequest(BaseModel):
    refresh_token: str
    model_config = ConfigDict(json_schema_extra={
        "example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR..."}
    })

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole
    # Per-store role (e.g. 'tenant_admin', 'customer') for the tenant_slug
    # given at login -- distinct from `role` above, which is the user's
    # global account role and is 'user' even for someone who administers a
    # store, since that permission lives in UserStoreMembership, not on User.
    store_role: Optional[str] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR...",
            "token_type": "bearer",
            "user_id": 12,
            "role": "user",
            "store_role": "tenant_admin"
        }
    })

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8)
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "full_name": "Yair K",
            "password": "newSecurePassword2026!"
        }
    })

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 12,
            "email": "customer@shop.com",
            "full_name": "John Doe",
            "role": "user",
            "is_active": True,
            "created_at": "2026-08-09T10:00:00Z"
        }
    })

class CustomerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "email": "customer@shop.com",
            "password": "mySecurePassword123",
            "full_name": "John Doe"
        }
    })

class CustomerSummaryResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime
    orders_count: int
    total_spent: float
    last_order_at: Optional[datetime] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 12,
            "email": "customer@shop.com",
            "full_name": "John Doe",
            "created_at": "2026-08-09T10:00:00Z",
            "orders_count": 4,
            "total_spent": 312.50,
            "last_order_at": "2026-08-10T08:00:00Z"
        }
    })

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    tenant_id: Optional[int]
    action: str
    ip_address: str
    created_at: datetime

class PaginatedAuditLogResponse(PaginatedResponse):
    data: List[AuditLogResponse]
