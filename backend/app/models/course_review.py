from sqlalchemy import Column, String, Integer, DateTime, Text, DECIMAL, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import uuid

def uuid_str():
    return str(uuid.uuid4())

class CourseReview(Base):
    __tablename__ = "course_reviews"

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    moderated_by = Column(String(36), ForeignKey("users.id"))

    rating_content = Column(Integer)
    rating_teacher = Column(Integer)
    rating_support = Column(Integer)
    overall_rating = Column(DECIMAL(3, 2))

    title = Column(String(200))
    comment = Column(Text)
    is_anonymous = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    reported_count = Column(Integer, default=0)

    status = Column(Enum('pending', 'approved', 'rejected', name='review_status_enum'), default='pending')
    moderated_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === Quan hệ ORM ===
    course = relationship("Course", back_populates="reviews", foreign_keys=[course_id])

    # 🔹 Người viết đánh giá
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="course_reviews",
        overlaps="moderated_reviews"
    )

    # 🔹 Người duyệt đánh giá (admin)
    moderator = relationship(
        "User",
        foreign_keys=[moderated_by],
        back_populates="moderated_reviews",
        overlaps="course_reviews"
    )

    def __repr__(self):
        return f"<CourseReview(user_id={self.user_id}, rating={self.overall_rating}, status={self.status})>"
