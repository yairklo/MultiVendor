from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.db.tenant_scope import TenantScoped

class AIPendingAction(TenantScoped, Base):
    """
    A destructive action (delete_product, cancelling an order) the AI has
    proposed but not executed — it only runs once a human confirms it through
    a real UI button (see ai_pending_action_service.py). One-time use: deleted
    on confirm or cancel.
    """
    __tablename__ = "ai_pending_actions"
    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_args = Column(JSON, nullable=False)
    summary = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
