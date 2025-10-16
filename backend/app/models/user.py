from sqlalchemy import Column, String, Integer, Date, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum
import uuid


# ===== Enums =====
class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class RoleEnum(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"
    teaching_assistant = "teaching_assistant"
    prospective_student = "prospective_student"


class StatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    graduated = "graduated"
    suspended = "suspended"
    pending_enrollment = "pending_enrollment"


# ===== User Model =====
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)

    # ===== Thông tin học vụ =====
    mssv = Column(String(20), unique=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id"), nullable=True)
    major_id = Column(String(36), ForeignKey("majors.id"), nullable=True)

    # ===== Quan hệ ORM =====
    academic_year = relationship("AcademicYear", back_populates="users")
    major = relationship("Major", back_populates="users")

    # ✅ Quan hệ ngược lại với Class (giáo viên chủ nhiệm)
    homeroom_classes = relationship(
        "Class",
        back_populates="homeroom_teacher",
        foreign_keys="Class.homeroom_teacher_id",
        cascade="all, delete-orphan"
    )

    # ✅ Quan hệ 1-1 với SecuritySetting
    security_setting = relationship(
        "SecuritySetting",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # ===== Thông tin cá nhân =====
    phone = Column(String(20))
    avatar_url = Column(String(500))
    date_of_birth = Column(Date)
    gender = Column(Enum(GenderEnum))

    # ===== Vai trò và trạng thái =====
    role = Column(Enum(RoleEnum), default=RoleEnum.student)
    status = Column(Enum(StatusEnum), default=StatusEnum.active)

    # ===== Thống kê học tập =====
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    total_learning_time = Column(Integer, default=0)

    # ===== Thời gian tạo / cập nhật =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # ===== Quan hệ mở rộng =====
    courses_taught = relationship("Course", back_populates="teacher", foreign_keys="Course.teacher_id")

    course_reviews = relationship(
        "CourseReview",
        back_populates="user",
        foreign_keys="CourseReview.user_id",
        cascade="all, delete-orphan"
    )

    enrollments = relationship("Enrollment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}', status='{self.status}')>"
