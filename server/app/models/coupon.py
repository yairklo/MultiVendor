from sqlalchemy import Column, Integer, BigInteger, String, Enum, DateTime, ForeignKey, Numeric, Boolean
from app.db.base_class import Base
from app.db.tenant_scope import TenantScoped

class Coupon(TenantScoped, Base):
    __tablename__ = "coupons"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False)
    discount_type = Column(Enum('percentage', 'fixed'), nullable=False)
    discount_val = Column(Numeric(10, 2), nullable=False)
    min_order_amt = Column(Numeric(10, 2), default=0.00)
    usage_limit = Column(Integer, default=0)
    used_count = Column(Integer, default=0)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
