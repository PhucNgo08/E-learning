"""
📁 Admin Routers Package
Tự động gom tất cả router của phần quản trị hệ thống (Admin).
"""

from fastapi import APIRouter

# --- Import tuyệt đối từng module admin (tránh vòng lặp import) ---
import app.routers.admin.dashboard as dashboard
import app.routers.admin.user_management as user_management
import app.routers.admin.course_management as course_management
import app.routers.admin.course_section as course_section
import app.routers.admin.course_category as course_category
import app.routers.admin.class_management as class_management
import app.routers.admin.enrollment_management as enrollment_management
import app.routers.admin.backup_management as backup_management
import app.routers.admin.exam_management as exam_management
import app.routers.admin.report_management as report_management
import app.routers.admin.course_review as course_review
import app.routers.admin.academic_years as academic_years
import app.routers.admin.settings as settings
import app.routers.admin.majors as majors
import app.routers.admin.teacher_management as teacher_management
import app.routers.admin.assignment as assignment
import app.routers.admin.course_material as course_material
import app.routers.admin.quiz_template as quiz_template
import app.routers.admin.quiz as quiz
import app.routers.admin.module_reorder as module_reorder
import app.routers.admin.discussion_management as discussion               # 🆕 Thảo luận
import app.routers.admin.file_storage_management as file_storage_management  # 🆕 Quản lý file
import app.routers.admin.notification_management as notification           # 🆕 Thông báo


# --- Khởi tạo router gốc cho admin ---
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# --- Include từng module con ---
admin_router.include_router(dashboard.dashboard_router)
admin_router.include_router(user_management.user_router)
admin_router.include_router(course_management.course_router)
admin_router.include_router(course_section.section_router)
admin_router.include_router(course_category.category_router)
admin_router.include_router(class_management.class_router)
admin_router.include_router(enrollment_management.enrollment_router)
admin_router.include_router(backup_management.backup_router)
admin_router.include_router(exam_management.exam_router)
admin_router.include_router(report_management.report_router)
admin_router.include_router(course_review.review_router)
admin_router.include_router(academic_years.router)
admin_router.include_router(settings.router)
admin_router.include_router(majors.router)
admin_router.include_router(teacher_management.router)
admin_router.include_router(assignment.router)
admin_router.include_router(course_material.router)
admin_router.include_router(quiz_template.router)
admin_router.include_router(quiz.router)
admin_router.include_router(module_reorder.router)

# --- 🆕 Thêm 3 router mới ---
admin_router.include_router(discussion.router)
admin_router.include_router(file_storage_management.router)
admin_router.include_router(notification.router)


__all__ = [
    "admin_router",
    "dashboard",
    "user_management",
    "course_management",
    "course_section",
    "course_category",
    "class_management",
    "enrollment_management",
    "backup_management",
    "exam_management",
    "report_management",
    "course_review",
    "academic_years",
    "settings",
    "majors",
    "teacher_management",
    "assignment",
    "course_material",
    "quiz_template",
    "quiz",
    "module_reorder",
    "discussion",
    "file_storage_management",
    "notification",
]
