from .academic_year import AcademicYear
from .api_endpoint import ApiEndpoint
from .api_rate_limit import ApiRateLimit
from .api_request_log import ApiRequestLog
from .attempt_answer import AttemptAnswer
from .backup_history import BackupHistory
from .backup_schedule import BackupSchedule
from .cdn_cache import CdnCache
from .class_schedule import ClassSchedule
from .classes import Class
from .course_category import CourseCategory
from .course_material import CourseMaterial
from .course_review import CourseReview
from .course_section import CourseSection
from .course import Course
from .database_health_log import DatabaseHealthLog
from .enrollment import Enrollment
from .file_storage import FileStorage
from .lesson_progress import LessonProgress
from .lesson import Lesson
from .major import Major
from .module import Module
from .question_bank import QuestionBank
from .question_option import QuestionOption
from .question import Question
from .quiz_attempt import QuizAttempt
from .quiz_template import QuizTemplate
from .quiz import Quiz
from .security_setting import SecuritySetting
from .storage_analytics import StorageAnalytics
from .user import User
from .exam import Exam  # Đảm bảo import Exam ở đây
from .report import Report  # Đảm bảo import Report ở đây
from .assignment import Assignment   # ✅ Thêm dòng này
# from .tag import Tag    
# from .user_activity_log import UserActivityLog
# from .user_notification import UserNotification
# from .user_role import UserRole
# from .user_setting import UserSetting