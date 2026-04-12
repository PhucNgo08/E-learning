from datetime import datetime
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str():
    return str(uuid.uuid4())


class UserCourse(Base):
    """
    Legacy compatibility model.

    Bảng này chỉ còn giữ để:
    - tương thích dữ liệu cũ,
    - backfill sang course_enrollments,
    - truy vết lịch sử migration / purchase cũ.

    Không dùng làm nguồn sự thật quyền học nữa.
    """

    __tablename__ = "user_courses"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)

    # legacy mapping tới order cũ
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)

    purchased_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    access_status = Column(String(20), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_user_courses"),
        Index("ix_user_courses_user_id", "user_id"),
        Index("ix_user_courses_course_id", "course_id"),
    )

    user = relationship("User", back_populates="user_courses")
    course = relationship("Course", back_populates="user_courses")
    order = relationship("Order", back_populates="user_courses")

    def __repr__(self):
        return (
            f"<UserCourse user={self.user_id} course={self.course_id} "
            f"order={self.order_id} access_status={self.access_status}>"
        )