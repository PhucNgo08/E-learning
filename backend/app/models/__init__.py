# =============================================
# 📦 app/models/__init__.py
# Tập hợp tất cả model để SQLAlchemy load đúng thứ tự
# =============================================

# === Core & Academic Models ===
from .academic_year import AcademicYear
from .major import Major
from .classes import Class
from .enrollment import Enrollment
from .user import User

# === Course System ===
from .course_category import CourseCategory
from .course import Course
from .course_section import CourseSection
from .module import Module
from .lesson import Lesson
from .lesson_progress import LessonProgress
from .course_material import CourseMaterial
from .course_review import CourseReview

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

# === System & Security ===
from .security_setting import SecuritySettings

from .api_endpoint import ApiEndpoint
from .api_rate_limit import ApiRateLimit
from .api_request_log import ApiRequestLog
from .backup_history import BackupHistory
from .backup_schedule import BackupSchedule
from .cdn_cache import CDNCache as CdnCache 
from .database_health_log import DatabaseHealthLog
from .file_storage import FileStorage
from .storage_analytics import StorageAnalytics
from .report import Report
from .exam import Exam
# ... các import khác

from .discussion import Discussion
from .discussion_like import DiscussionLike