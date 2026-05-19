from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.connection import Base
import uuid
from sqlalchemy.sql import func


class SecuritySettings(Base):
    __tablename__ = "security_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # 🧩 Cấu hình bảo mật
    two_factor_enabled = Column(Boolean, default=False)
    last_password_change = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 🔗 Liên kết ngược lại với User
    user = relationship("User", back_populates="security_setting")

    # 🔒 Đảm bảo mỗi user chỉ có 1 cấu hình bảo mật
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_security"),)
