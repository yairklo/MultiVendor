from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, BigInteger, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.db.tenant_scope import TenantScoped


class TenantShippingConfig(TenantScoped, Base):
    # One row per (tenant, courier) pair a vendor has connected -- a vendor
    # may configure more than one courier, with is_default picking which one
    # fulfill_order_service uses when the caller doesn't name one explicitly.
    # credentials_encrypted holds a Fernet-encrypted JSON blob (see
    # app/core/crypto.py) whose shape depends on `provider`
    # ({"auth_token": ..., "client_number": ...} for hfd,
    # {"api_key": ..., "company_id": ...} for lionwheel) -- kept as one
    # encrypted column rather than provider-specific plaintext columns so
    # adding a third provider never needs a schema migration for its
    # credential shape.
    #
    # sender_* below is the pickup address every courier shipment needs as
    # its "from" -- there was nowhere else to put this (neither Tenant nor
    # TenantSettings has a phone or address field at all), and it lives here
    # rather than as a new platform-wide "store address" concept because a
    # courier account is literally issued against one pickup location, so
    # this is the correct scope for it, not a workaround.
    __tablename__ = "tenant_shipping_configs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Enum("hfd", "lionwheel"), nullable=False)
    credentials_encrypted = Column(Text, nullable=False)
    sender_name = Column(String(255), nullable=False)
    sender_phone = Column(String(20), nullable=False)
    sender_city = Column(String(100), nullable=False)
    sender_street = Column(String(255), nullable=False)
    sender_house_number = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_tenant_shipping_provider"),
    )
