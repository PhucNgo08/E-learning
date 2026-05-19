from datetime import datetime

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.models.assignment import Assignment
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.quiz import Quiz
from app.models.user import User
from app.utils.user_query import filter_users_by_role


dashboard_router = APIRouter(
    prefix="/admin",
    tags=["Admin - Dashboard"],
)


def _require_admin(request: Request):
    """
    Chỉ cho phép admin vào trang dashboard.
    Nếu chưa đăng nhập hoặc không phải admin thì chuyển về login.
    """
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)
    return None


def _safe_count(query) -> int:
    """
    Tránh lỗi None khi query count không trả về dữ liệu.
    """
    return int(query.scalar() or 0)


def _serialize_datetime(value):
    """
    Dùng cho JSONResponse vì datetime không tự chuyển sang JSON được.
    Template HTML vẫn có thể dùng datetime gốc bình thường.
    """
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else value


def get_recent_courses(db: Session, limit: int = 5):
    courses = (
        db.query(Course)
        .options(
            joinedload(Course.teacher).joinedload(User.profile),
        )
        .filter(Course.deleted_at.is_(None))
        .order_by(Course.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []

    for course in courses:
        teacher = getattr(course, "teacher", None)
        teacher_profile = getattr(teacher, "profile", None) if teacher else None

        result.append(
            {
                "id": course.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "status": course.status,
                "teacher_name": (
                    getattr(teacher_profile, "full_name", None)
                    or getattr(teacher, "username", None)
                    or "Chưa phân công"
                ),
                "created_at": course.created_at,
            }
        )

    return result


def get_dashboard_stats(db: Session) -> dict:
    total_users = _safe_count(
        db.query(func.count(User.id)).filter(User.deleted_at.is_(None))
    )

    total_teachers = filter_users_by_role(
        db.query(User),
        "teacher",
    ).count()

    total_students = filter_users_by_role(
        db.query(User),
        "student",
    ).count()

    total_courses = _safe_count(
        db.query(func.count(Course.id)).filter(Course.deleted_at.is_(None))
    )

    published_courses = _safe_count(
        db.query(func.count(Course.id)).filter(
            Course.deleted_at.is_(None),
            Course.status == "published",
        )
    )

    draft_courses = _safe_count(
        db.query(func.count(Course.id)).filter(
            Course.deleted_at.is_(None),
            Course.status == "draft",
        )
    )

    archived_courses = _safe_count(
        db.query(func.count(Course.id)).filter(
            Course.deleted_at.is_(None),
            Course.status == "archived",
        )
    )

    total_enrollments = _safe_count(
        db.query(func.count(CourseEnrollment.id))
        .join(Course, CourseEnrollment.course_id == Course.id)
        .filter(Course.deleted_at.is_(None))
    )

    active_enrollments = _safe_count(
        db.query(func.count(CourseEnrollment.id))
        .join(Course, CourseEnrollment.course_id == Course.id)
        .filter(
            Course.deleted_at.is_(None),
            CourseEnrollment.enrollment_status.in_(
                ["approved", "active", "completed"]
            ),
        )
    )

    total_assignments = _safe_count(
        db.query(func.count(Assignment.id))
    )

    total_quizzes = _safe_count(
        db.query(func.count(Quiz.id))
    )

    return {
        "total_users": total_users,
        "total_teachers": total_teachers,
        "total_students": total_students,
        "total_courses": total_courses,
        "published_courses": published_courses,
        "draft_courses": draft_courses,
        "archived_courses": archived_courses,
        "total_enrollments": total_enrollments,
        "active_enrollments": active_enrollments,
        "total_assignments": total_assignments,
        "total_quizzes": total_quizzes,
    }


def serialize_recent_courses_for_json(recent_courses: list[dict]) -> list[dict]:
    """
    Bản dành riêng cho API JSON, tránh lỗi datetime không serialize được.
    """
    return [
        {
            **course,
            "created_at": _serialize_datetime(course.get("created_at")),
        }
        for course in recent_courses
    ]


@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    format: str | None = Query(None),
):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    try:
        stats = get_dashboard_stats(db)
        recent_courses = get_recent_courses(db)

        data = {
            "request": request,
            "stats": stats,
            "recent_courses": recent_courses,
            "now": datetime.now(),
        }

        if format == "json":
            return JSONResponse(
                {
                    "ok": True,
                    "stats": stats,
                    "recent_courses": serialize_recent_courses_for_json(
                        recent_courses
                    ),
                }
            )

        # get_template_by_path("/admin/dashboard") đã trỏ vào thư mục templates/admin
        # nên ở đây chỉ truyền tên file template, không truyền "admin/...".
        tpl = get_template_by_path(request.url.path)
        return tpl.TemplateResponse(
            "admin_dashboard.html",
            data,
        )

    except Exception as e:
        if format == "json":
            return JSONResponse(
                {
                    "ok": False,
                    "error": "Internal Server Error",
                    "message": str(e),
                },
                status_code=500,
            )

        raise
