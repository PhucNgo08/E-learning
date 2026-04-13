# =============================================
# app/models/__init__.py
# Tập hợp tất cả model để SQLAlchemy load đúng thứ tự
# =============================================

# === Misc / Existing ===
from .question_bank_option import QuestionBankOption
from .course_material_version import CourseMaterialVersion


from .wallet_accounts import WalletAccount
from .wallet_transactions import WalletTransaction
from .wallet_topup_request import WalletTopupRequest

# === Core & Academic ===
from .academic_year import AcademicYear
from .major import Major
from .classes import Class
from .class_enrollment import ClassEnrollment
from .course_enrollment import CourseEnrollment
from .user import User
from .user_profile import UserProfile
from .student_profile import StudentProfile
from .teacher_profiles import TeacherProfile
from .system_settings import SystemSetting
from .security_setting import SecuritySettings
from .class_schedule import ClassSchedule

# === RBAC / Security Extension ===
from .rbac import Role, Permission, user_roles, role_permissions

# === Course System ===
from .course_category import CourseCategory
from .course import Course
from .course_section import CourseSection
from .module import Module
from .lesson import Lesson
from .lesson_progress import LessonProgress
from .lesson_note import LessonNote
from .course_progress import CourseProgress
from .learning_activity_log import LearningActivityLog
from .course_material import CourseMaterial
from .course_review import CourseReview
from .certificate import Certificate

# === Quiz & Question System ===
from .quiz import Quiz
from .quiz_attempt import QuizAttempt
from .question import Question
from .question_option import QuestionOption
from .question_bank import QuestionBank
from .quiz_template import QuizTemplate
from .attempt_answer import AttemptAnswer

# === Assignment System ===
from .assignment import Assignment
from .assignment_submission import AssignmentSubmission
from .assignment_group import AssignmentGroup
from .assignment_file import AssignmentFile

# === E-Commerce System ===
from .cart_item import CartItem
from .order import Order
from .order_item import OrderItem
from .user_course import UserCourse

# === Messaging & Notification ===
from .message import Message
from .notification import Notification
from .discussion import Discussion
from .discussion_like import DiscussionLike

# === AI System ===
from .ai_chat_history import AIChatHistory

# === File storage & CDN ===
from .file_storage import FileStorage
from .cdn_cache import CDNCache
from .storage_analytics import StorageAnalytics

# === API Rate Limit / Logging ===
from .api_endpoint import ApiEndpoint
from .api_request_log import ApiRequestLog
from .api_rate_limit import ApiRateLimit

# === Backup System ===
from .backup_history import BackupHistory
from .backup_schedule import BackupSchedule
from .database_health_log import DatabaseHealthLog