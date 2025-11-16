from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid

def uuid_str():
    return str(uuid.uuid4())

class UserCourse(Base):
    __tablename__ = "user_courses"

    id = Column(String(36), primary_key=True, default=uuid_str)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)

    # Không cho mua trùng khóa học
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uix_user_course"),
    )

    user = relationship("User", back_populates="user_courses")
    course = relationship("Course", back_populates="user_courses")

    def __repr__(self):
        return f"<UserCourse user={self.user_id} course={self.course_id}>"
