from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Text, Enum,
    ForeignKey, Boolean, DECIMAL
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
    description = Column(Text)
    credit_hours = Column(Integer, default=3)

    course_type = Column(Enum("mandatory", "elective", "workshop", "online", "hybrid",
                              name="course_type_enum"), default="mandatory")
    subject = Column(String(100))
    grade_level = Column(Integer)
    difficulty_level = Column(Enum("beginner", "intermediate", "advanced",
                                   name="difficulty_enum"), default="beginner")

    teacher_id = Column(String(36), ForeignKey("users.id"))
    academic_year_id = Column(String(36), ForeignKey("academic_years.id"))
    major_id = Column(String(36), ForeignKey("majors.id"))

    semester = Column(Integer)
    status = Column(Enum("draft", "published", "archived",
                         name="course_status_enum"), default="draft")
    enrollment_mode = Column(Enum("auto", "approval", "invite_only",
                                  name="enrollment_mode_enum"), default="auto")

    max_students = Column(Integer, default=100)
    current_students = Column(Integer, default=0)

    # Recommended: Boolean
    is_public = Column(Boolean, default=False)

    # E-commerce fields
    price = Column(DECIMAL(10, 2, asdecimal=True), default=0)
    discount_percent = Column(Integer, default=0)

    start_date = Column(Date)
    end_date = Column(Date)

    thumbnail_url = Column(String(500))
    prerequisites = Column(Text)

    allow_assignments = Column(Boolean, default=True)
    default_submission_type = Column(Enum("individual", "group",
                                          name="default_submission_enum"), default="individual")
    assignment_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    teacher = relationship("User", back_populates="courses_taught", foreign_keys=[teacher_id])
    academic_year = relationship("AcademicYear", back_populates="courses")
    major = relationship("Major", back_populates="courses")

    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan")
    reviews = relationship("CourseReview", back_populates="course", cascade="all, delete-orphan")
    materials = relationship("CourseMaterial", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="course", cascade="all, delete-orphan")

    user_courses = relationship("UserCourse", back_populates="course", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="course", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="course", cascade="all, delete-orphan")
    sections = relationship("CourseSection", back_populates="course", cascade="all, delete")

    def __repr__(self):
        return f"<Course(code='{self.course_code}', name='{self.course_name}')>"
