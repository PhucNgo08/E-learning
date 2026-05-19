from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=uuid_str)

    course_code = Column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    course_name = Column(String(200), nullable=False)
    description = Column(Text)

    credit_hours = Column(Integer, nullable=False, default=3)

    course_type = Column(
        String(30),
        nullable=False,
        default="mandatory",
    )

    subject_name = Column(String(100))
    grade_level = Column(Integer)

    difficulty_level = Column(
        String(30),
        nullable=False,
        default="beginner",
    )

    teacher_id = Column(
        String(36),
        ForeignKey("users.id"),
        index=True,
    )

    academic_year_id = Column(
        String(36),
        ForeignKey("academic_years.id"),
        index=True,
    )

    major_id = Column(
        String(36),
        ForeignKey("majors.id"),
        index=True,
    )

    semester = Column(Integer)

    price = Column(
        DECIMAL(10, 2),
        nullable=False,
        default=0,
    )

    discount_percent = Column(
        Integer,
        nullable=False,
        default=0,
    )

    status = Column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
    )

    enrollment_mode = Column(
        String(30),
        nullable=False,
        default="auto",
    )

    max_students = Column(
        Integer,
        nullable=False,
        default=100,
    )

    current_students = Column(
        Integer,
        nullable=False,
        default=0,
    )

    is_public = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    start_date = Column(Date)
    end_date = Column(Date)

    thumbnail_url = Column(String(500))
    prerequisites = Column(Text)

    allow_assignments = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    default_submission_type = Column(
        String(20),
        nullable=False,
        default="individual",
    )

    assignment_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

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

    deleted_at = Column(
        DateTime,
        nullable=True,
        index=True,
    )

    # =========================================================
    # RELATIONSHIPS
    # =========================================================

    teacher = relationship(
        "User",
        back_populates="courses_taught",
        foreign_keys=[teacher_id],
        lazy="selectin",
    )

    academic_year = relationship(
        "AcademicYear",
        back_populates="courses",
        lazy="selectin",
    )

    major = relationship(
        "Major",
        back_populates="courses",
        lazy="selectin",
    )

    modules = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    reviews = relationship(
        "CourseReview",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    materials = relationship(
        "CourseMaterial",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    assignments = relationship(
        "Assignment",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Nguồn sự thật quyền học
    course_enrollments = relationship(
        "CourseEnrollment",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    discussions = relationship(
        "Discussion",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Legacy compatibility only
    user_courses = relationship(
        "UserCourse",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    cart_items = relationship(
        "CartItem",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    order_items = relationship(
        "OrderItem",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    sections = relationship(
        "CourseSection",
        back_populates="course",
        cascade="all, delete",
        lazy="selectin",
    )

    quizzes = relationship(
        "Quiz",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    course_progresses = relationship(
        "CourseProgress",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    learning_activity_logs = relationship(
        "LearningActivityLog",
        back_populates="course",
        lazy="selectin",
    )

    # =========================================================
    # HELPERS
    # =========================================================

    @property
    def subject(self):
        return self.subject_name

    def __repr__(self) -> str:
        return (
            f"<Course("
            f"code='{self.course_code}', "
            f"name='{self.course_name}', "
            f"status='{self.status}'"
            f")>"
        )