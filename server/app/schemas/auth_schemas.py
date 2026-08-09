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

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole
    tenant_id: Optional[int] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR...",
            "token_type": "bearer",
            "user_id": 12,
            "role": "tenant_admin",
            "tenant_id": 1
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
    tenant_id: Optional[int]
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 12,
            "tenant_id": 1,
            "email": "customer@shop.com",
            "full_name": "John Doe",
            "role": "customer",
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

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    tenant_id: Optional[int]
    action: str
    ip_address: str
    created_at: datetime

class PaginatedAuditLogResponse(PaginatedResponse):
    data: List[AuditLogResponse]
