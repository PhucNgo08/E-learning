"""
📁 Admin Routers Package
Tự động gom tất cả router của phần quản trị hệ thống (Admin).
"""

from fastapi import APIRouter

# --- Import tất cả router admin ---
from app.routers.admin import (
    dashboard,
    user_management,
    course_management,
    course_section,
    course_category,
    class_management,
    enrollment_management,
    backup_management,
    exam_management,
    report_management,
    course_review,
    academic_years,
    settings,
    majors,
    teacher_management,
    assignment,
    course_material,
    quiz_template,
    quiz,
)

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

# --- Các module mới bổ sung ---
admin_router.include_router(assignment.router)
admin_router.include_router(course_material.router)
admin_router.include_router(quiz_template.router)
admin_router.include_router(quiz.router)

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
]
