from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
import uuid


class SecuritySetting(Base):
    __tablename__ = "security_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    two_factor_enabled = Column(Boolean, default=False)
    last_password_change = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)

    # 🔗 Liên kết ngược lại với User
    user = relationship("User", back_populates="security_setting")
