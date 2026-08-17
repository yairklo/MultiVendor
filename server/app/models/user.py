from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Enum, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    # Global role: distinguishes the platform super admin from every other
    # (global) account. Store-level roles (tenant_admin / customer) live on
    # UserStoreMembership, since one identity can now hold different roles
    # at different stores.
    role = Column(Enum('super_admin', 'user'), nullable=False, default='user')
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    memberships = relationship("UserStoreMembership", back_populates="user", cascade="all, delete-orphan")

class UserStoreMembership(Base):
    __tablename__ = "user_store_memberships"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum('tenant_admin', 'customer'), nullable=False, default='customer')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'tenant_id', name='uq_user_tenant'),)

    user = relationship("User", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="memberships")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=True)
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
