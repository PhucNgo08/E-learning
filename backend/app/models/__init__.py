# =============================================
# 📦 app/models/__init__.py
# Tập hợp tất cả model để SQLAlchemy load đúng thứ tự
# =============================================

# === Core & Academic (Nền tảng) ===
from .academic_year import AcademicYear
from .major import Major
from .classes import Class
from .enrollment import Enrollment
from .user import User
from .system_settings import SystemSetting        # ⭐ THÊM

# === Course System (Khóa học) ===
from .course_category import CourseCategory
from .course import Course
from .course_section import CourseSection        # ⭐ THÊM CHUẨN
from .module import Module
from .lesson import Lesson
from .lesson_progress import LessonProgress
from .lesson_note import LessonNote              # ⭐ THÊM
from .course_material import CourseMaterial
from .course_review import CourseReview

# === Quiz & Question System (Trắc nghiệm) ===
from .quiz import Quiz
from .quiz_attempt import QuizAttempt
from .question import Question
from .question_option import QuestionOption
from .question_bank import QuestionBank
from .quiz_template import QuizTemplate
from .attempt_answer import AttemptAnswer

# === Assignment System (Bài tập) ===
from .assignment import Assignment
from .assignment_submission import AssignmentSubmission
from .assignment_group import AssignmentGroup
from .assignment_file import AssignmentFile

# === E-Commerce System (Thanh toán / giỏ hàng / khóa học mua) ===
from .cart_item import CartItem
from .order import Order
from .order_item import OrderItem
from .user_course import UserCourse

# === Messaging & Notification (Tin nhắn & thông báo) ===
from .message import Message                     # ⭐ THÊM
from .notification import Notification
from .discussion import Discussion
   # ⭐ THÊM
from .discussion_like import DiscussionLike

# === AI System (Chat AI) ===
from .ai_chat_history import AIChatHistory       # ⭐ THÊM

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

# === Security ===
from .security_setting import SecuritySettings
from .class_schedule import ClassSchedule