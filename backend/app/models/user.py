import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # =====================================================
    # CORE PROFILE / SECURITY / RBAC
    # =====================================================
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    student_profile = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    teacher_profile = relationship(
        "TeacherProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    security_setting = relationship(
        "SecuritySettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )

    # =====================================================
    # CLASS / COURSE MANAGEMENT
    # =====================================================
    homeroom_classes = relationship(
        "Class",
        back_populates="homeroom_teacher",
        foreign_keys="Class.homeroom_teacher_id",
    )

    courses_taught = relationship(
        "Course",
        back_populates="teacher",
        foreign_keys="Course.teacher_id",
    )

    teaching_sections = relationship(
        "CourseSection",
        back_populates="teacher",
    )

    class_enrollments = relationship(
        "ClassEnrollment",
        back_populates="student",
        cascade="all, delete-orphan",
        foreign_keys="ClassEnrollment.student_id",
    )

    approved_class_enrollments = relationship(
        "ClassEnrollment",
        back_populates="approved_user",
        foreign_keys="ClassEnrollment.approved_by",
    )

    course_enrollments = relationship(
        "CourseEnrollment",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="CourseEnrollment.user_id",
    )

    approved_course_enrollments = relationship(
        "CourseEnrollment",
        back_populates="approved_user",
        foreign_keys="CourseEnrollment.approved_by",
    )

    # =====================================================
    # REVIEWS / ASSIGNMENTS / QUIZZES
    # =====================================================
    course_reviews = relationship(
        "CourseReview",
        back_populates="user",
        foreign_keys="CourseReview.user_id",
        overlaps="moderated_reviews",
    )

    moderated_reviews = relationship(
        "CourseReview",
        back_populates="moderator",
        foreign_keys="CourseReview.moderated_by",
        overlaps="course_reviews",
    )

    assignments_created = relationship(
        "Assignment",
        back_populates="teacher",
        foreign_keys="Assignment.teacher_id",
    )

    assignment_submissions = relationship(
        "AssignmentSubmission",
        back_populates="student",
        foreign_keys="AssignmentSubmission.student_id",
    )

    graded_assignment_submissions = relationship(
        "AssignmentSubmission",
        back_populates="grader",
        foreign_keys="AssignmentSubmission.graded_by",
    )

    assignment_groups_led = relationship(
        "AssignmentGroup",
        back_populates="leader",
        foreign_keys="AssignmentGroup.leader_id",
    )

    quiz_attempts = relationship(
        "QuizAttempt",
        back_populates="user",
        foreign_keys="QuizAttempt.user_id",
        overlaps="graded_quiz_attempts",
    )

    graded_quiz_attempts = relationship(
        "QuizAttempt",
        back_populates="graded_by_user",
        foreign_keys="QuizAttempt.graded_by",
        overlaps="quiz_attempts",
    )

    quiz_templates = relationship(
        "QuizTemplate",
        back_populates="creator",
        foreign_keys="QuizTemplate.created_by",
        cascade="all, delete-orphan",
    )

    # =====================================================
    # DISCUSSION / MESSAGE / NOTIFICATION / AI
    # =====================================================
    discussions = relationship(
        "Discussion",
        back_populates="user",
        cascade="all, delete",
    )

    discussion_likes = relationship(
        "DiscussionLike",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    messages_sent = relationship(
        "Message",
        back_populates="sender",
        foreign_keys="Message.sender_id",
        cascade="all, delete-orphan",
    )

    messages_received = relationship(
        "Message",
        back_populates="receiver",
        foreign_keys="Message.receiver_id",
        cascade="all, delete-orphan",
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    ai_chat_history = relationship(
        "AIChatHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    lesson_notes = relationship(
        "LessonNote",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # =====================================================
    # CART / ORDER / WALLET / ACCESS
    # =====================================================
    cart_items = relationship(
        "CartItem",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    wallet = relationship(
        "WalletAccount",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
    )

    wallet_topup_requests = relationship(
        "WalletTopupRequest",
        back_populates="user",
        foreign_keys="WalletTopupRequest.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    reviewed_wallet_topup_requests = relationship(
        "WalletTopupRequest",
        back_populates="reviewer",
        foreign_keys="WalletTopupRequest.reviewed_by",
        lazy="selectin",
    )

    # Legacy compatibility only
    user_courses = relationship(
        "UserCourse",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    certificates = relationship(
        "Certificate",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    lesson_progresses = relationship("LessonProgress", back_populates="user", cascade="all, delete-orphan")
    course_progresses = relationship("CourseProgress", back_populates="user", cascade="all, delete-orphan")
    learning_activity_logs = relationship("LearningActivityLog", back_populates="user", cascade="all, delete-orphan")

    # =====================================================
    # READ-ONLY COMPATIBILITY HELPERS
    # =====================================================
    @property
    def user_profile(self):
        # Alias tương thích với code/template cũ.
        return self.profile

    @property
    def wallet_account(self):
        # Alias tương thích với code cũ.
        return self.wallet

    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.deleted_at is None

    def has_role(self, role_code: str) -> bool:
        return any(role.role_code == role_code for role in (self.roles or []))

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
        self.status = "inactive"

    def restore(self):
        self.deleted_at = None
        self.status = "active"

    @property
    def full_name(self):
        return self.profile.full_name if self.profile else None

    @property
    def phone(self):
        return self.profile.phone if self.profile else None

    @property
    def avatar_url(self):
        return self.profile.avatar_url if self.profile else None

    @property
    def date_of_birth(self):
        return self.profile.date_of_birth if self.profile else None

    @property
    def gender(self):
        return self.profile.gender if self.profile else None

    @property
    def mssv(self):
        return self.student_profile.mssv if self.student_profile else None

    @property
    def employee_code(self):
        return self.teacher_profile.employee_code if self.teacher_profile else None

    @property
    def academic_year_id(self):
        return self.student_profile.academic_year_id if self.student_profile else None

    @property
    def academic_year(self):
        return self.student_profile.academic_year if self.student_profile else None

    @property
    def major_id(self):
        if self.teacher_profile and self.teacher_profile.major_id:
            return self.teacher_profile.major_id
        return self.student_profile.major_id if self.student_profile else None

    @property
    def major(self):
        if self.teacher_profile and self.teacher_profile.major:
            return self.teacher_profile.major
        return self.student_profile.major if self.student_profile else None

    @property
    def points(self):
        return self.student_profile.points if self.student_profile else 0

    @property
    def level(self):
        return self.student_profile.level_no if self.student_profile else 1

    @property
    def total_learning_time(self):
        return self.student_profile.total_learning_time if self.student_profile else 0

    @property
    def total_assignments_submitted(self):
        return self.student_profile.total_assignments_submitted if self.student_profile else 0

    @property
    def total_assignments_graded(self):
        return self.student_profile.total_assignments_graded if self.student_profile else 0

    @property
    def total_assignments_created(self):
        return self.teacher_profile.total_assignments_created if self.teacher_profile else 0

    @property
    def role(self):
        if not self.roles:
            return None

        priority = ["admin", "teacher", "teaching_assistant", "student"]
        role_codes = [getattr(role, "role_code", None) for role in self.roles]
        for code in priority:
            if code in role_codes:
                return code
        return role_codes[0]

    def __repr__(self):
        return (
            f"<User(username='{self.username}', email='{self.email}', "
            f"status='{self.status}')>"
        )