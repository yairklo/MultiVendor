from typing import List
from pydantic import BaseModel
from enum import Enum

class UserRole(str, Enum):
    """Global identity role. Store-level roles live on membership, see MembershipRole."""
    SUPER_ADMIN = "super_admin"
    USER = "user"

class MembershipRole(str, Enum):
    """A single global user can hold a different one of these per store, via
    UserStoreMembership."""
    TENANT_ADMIN = "tenant_admin"
    CUSTOMER = "customer"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PENDING_PAYMENT = "pending_payment"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"

class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"

class PlanCode(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int

class PaginatedResponse(BaseModel):
    meta: PaginationMeta
