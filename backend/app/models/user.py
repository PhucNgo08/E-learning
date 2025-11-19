from sqlalchemy import (
    Column, String, Integer, Date, DateTime, Text, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum
import uuid


# ============================================
# 🧩 ENUM DEFINITIONS
# ============================================
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


# ============================================
# 🧩 USER MODEL
# ============================================
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)

    # ===== Academic Info =====
    mssv = Column(String(20), unique=True)
    academic_year_id = Column(String(36), ForeignKey("academic_years.id"))
    major_id = Column(String(36), ForeignKey("majors.id"))

    academic_year = relationship("AcademicYear", back_populates="users")
    major = relationship("Major", back_populates="users")

    # ===== Relationship with Class =====
    homeroom_classes = relationship(
        "Class",
        back_populates="homeroom_teacher",
        foreign_keys="Class.homeroom_teacher_id",
        cascade="all, delete-orphan"
    )

    # ===== Security Setting =====
    security_setting = relationship(
        "SecuritySettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # ===== Personal Info =====
    phone = Column(String(20))
    avatar_url = Column(String(500))
    date_of_birth = Column(Date)
    gender = Column(Enum(GenderEnum))

    # ===== Role & Status =====
    role = Column(Enum(RoleEnum), default=RoleEnum.student)
    status = Column(Enum(StatusEnum), default=StatusEnum.active)

    # ===== Learning Stats =====
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    total_learning_time = Column(Integer, default=0)

    # ===== Assignment Tracking =====
    total_assignments_submitted = Column(Integer, default=0)
    total_assignments_graded = Column(Integer, default=0)
    total_assignments_created = Column(Integer, default=0)

    # ===== Timestamp =====
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(),
                        server_default=func.now())

    # ============================================
    # 🔗 RELATIONSHIPS
    # ============================================

    # === Course Management ===
    courses_taught = relationship(
        "Course",
        back_populates="teacher",
        foreign_keys="Course.teacher_id"
    )

    # === Course Reviews ===
    course_reviews = relationship(
        "CourseReview",
        back_populates="user",
        foreign_keys="CourseReview.user_id",
        overlaps="moderated_reviews"
    )
    moderated_reviews = relationship(
        "CourseReview",
        back_populates="moderator",
        foreign_keys="CourseReview.moderated_by",
        overlaps="course_reviews"
    )

    teaching_sections = relationship("CourseSection", back_populates="teacher")

    # ======================================================
    # 🔥 Enrollment (FIX FULL)
    # ======================================================

    # User → enrollments (FK: user_id)
    enrollments = relationship(
        "Enrollment",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Enrollment.user_id"
    )

    # User → enrollments (FK: approved_by)
    approved_enrollments = relationship(
        "Enrollment",
        back_populates="approved_user",
        foreign_keys="Enrollment.approved_by"
    )

    # ======================================================

    # === Assignments ===
    assignments_created = relationship(
        "Assignment",
        back_populates="teacher",
        foreign_keys="Assignment.teacher_id"
    )
    assignment_submissions = relationship(
        "AssignmentSubmission",
        back_populates="student",
        foreign_keys="AssignmentSubmission.student_id"
    )
    assignment_groups_led = relationship(
        "AssignmentGroup",
        back_populates="leader",
        foreign_keys="AssignmentGroup.leader_id"
    )

    # === Quiz Attempts ===
    quiz_attempts = relationship(
        "QuizAttempt",
        back_populates="user",
        foreign_keys="QuizAttempt.user_id",
        overlaps="graded_quiz_attempts"
    )
    graded_quiz_attempts = relationship(
        "QuizAttempt",
        back_populates="graded_by_user",
        foreign_keys="QuizAttempt.graded_by",
        overlaps="quiz_attempts"
    )

    # === Discussions ===
    discussions = relationship(
        "Discussion",
        back_populates="user",
        cascade="all, delete"
    )

    # === Cart / Orders / Purchased Courses ===
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    user_courses = relationship("UserCourse", back_populates="user", cascade="all, delete-orphan")

    # === Messages ===
    messages_sent = relationship(
        "Message",
        back_populates="sender",
        foreign_keys="Message.sender_id",
        cascade="all, delete-orphan"
    )
    messages_received = relationship(
        "Message",
        back_populates="receiver",
        foreign_keys="Message.receiver_id",
        cascade="all, delete-orphan"
    )

    # === Notifications ===
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # === AI Chat History ===
    ai_chat_history = relationship(
        "AIChatHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    quiz_templates = relationship(
    "QuizTemplate",
    back_populates="creator",
    foreign_keys="QuizTemplate.created_by",
    cascade="all, delete-orphan"
    )
    wallet = relationship(
    "WalletAccount",
    uselist=False,
    back_populates="user"
    )

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}', status='{self.status}')>"
