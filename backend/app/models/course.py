from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Text, Enum, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base
import uuid


def uuid_str():
    return str(uuid.uuid4())


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=uuid_str)
    course_code = Column(String(20), unique=True, nullable=False)
    course_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    credit_hours = Column(Integer, default=3)

    # ✅ Các trường về loại & cấp độ khóa học
    course_type = Column(Enum("mandatory", "elective", "workshop", "online", "hybrid", name="course_type_enum"), default="mandatory")
    subject = Column(String(100), nullable=True)
    grade_level = Column(Integer, nullable=True)
    difficulty_level = Column(Enum("beginner", "intermediate", "advanced", name="difficulty_enum"), default="beginner")

    # ✅ Liên kết học vụ
    teacher_id = Column(String(36), ForeignKey("users.id"))
    academic_year_id = Column(String(36), ForeignKey("academic_years.id"))
    major_id = Column(String(36), ForeignKey("majors.id"))

    semester = Column(Integer, nullable=True)
    status = Column(Enum("draft", "published", "archived", name="course_status_enum"), default="draft")
    enrollment_mode = Column(Enum("auto", "approval", "invite_only", name="enrollment_mode_enum"), default="auto")

    max_students = Column(Integer, default=100)
    current_students = Column(Integer, default=0)
    is_public = Column(Integer, default=0)

    # ✅ Thời gian học
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # ✅ Hình ảnh & mô tả
    thumbnail_url = Column(String(500), nullable=True)
    prerequisites = Column(Text, nullable=True)

    # 📘 Cấu hình bài tập (theo DB)
    allow_assignments = Column(Boolean, default=True)
    default_submission_type = Column(Enum("individual", "group", name="default_submission_enum"), default="individual")
    assignment_count = Column(Integer, default=0)

    # 🕓 Thời gian hệ thống
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # === Quan hệ ORM ===
    teacher = relationship("User", back_populates="courses_taught", foreign_keys=[teacher_id])
    academic_year = relationship("AcademicYear", back_populates="courses")
    major = relationship("Major", back_populates="courses")

    # 🔗 Quan hệ phụ thuộc
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    reviews = relationship("CourseReview", back_populates="course", cascade="all, delete-orphan")
    materials = relationship("CourseMaterial", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")

    # 💬 Thảo luận
    discussions = relationship("Discussion", back_populates="course", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Course(code='{self.course_code}', name='{self.course_name}')>"
