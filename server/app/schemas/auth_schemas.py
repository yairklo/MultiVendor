from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from app.schemas.common_schemas import UserRole, PaginatedResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole
    tenant_id: Optional[int] = None

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8)

class UserResponse(BaseModel):
    id: int
    tenant_id: Optional[int]
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CustomerRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    tenant_id: Optional[int]
    action: str
    ip_address: str
    created_at: datetime

class PaginatedAuditLogResponse(PaginatedResponse):
    data: List[AuditLogResponse]
