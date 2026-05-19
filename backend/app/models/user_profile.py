from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    full_name = Column(
        String(100),
        nullable=False,
    )

    phone = Column(String(20))
    avatar_url = Column(String(500))
    date_of_birth = Column(Date)
    gender = Column(String(20))

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="profile",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<UserProfile(user_id='{self.user_id}', full_name='{self.full_name}')>"