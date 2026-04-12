from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends, Query, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.rbac import Role


dashboard_router = APIRouter(
    prefix="/admin",
    tags=["Admin - Dashboard"]
)


def wants_json(request: Request, format: str | None = None) -> bool:
    """
    Xác định client muốn nhận JSON hay HTML.
    Ưu tiên:
    - ?format=json
    - header Accept: application/json
    """
    if format == "json":
        return True

    accept = request.headers.get("accept", "").lower()
    if "application/json" in accept:
        return True

    return False


def build_dashboard_stats(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_courses = db.query(func.count(Course.id)).scalar() or 0
    total_lessons = db.query(func.count(Lesson.id)).scalar() or 0

    total_teachers = (
        db.query(func.count(User.id))
        .join(User.roles)
        .filter(Role.role_code == "teacher")
        .scalar()
        or 0
    )

    total_students = (
        db.query(func.count(User.id))
        .join(User.roles)
        .filter(Role.role_code == "student")
        .scalar()
        or 0
    )

    return {
        "total_users": int(total_users),
        "total_courses": int(total_courses),
        "total_lessons": int(total_lessons),
        "total_teachers": int(total_teachers),
        "total_students": int(total_students),
    }


def get_recent_courses(db: Session, limit: int = 5) -> list[dict]:
    rows = (
        db.query(Course)
        .order_by(Course.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for course in rows:
        teacher_name = "Chưa gán"

        teacher = getattr(course, "teacher", None)
        if teacher:
            teacher_name = (
                getattr(teacher, "full_name", None)
                or getattr(getattr(teacher, "user_profile", None), "full_name", None)
                or getattr(teacher, "username", None)
                or "Chưa gán"
            )

        results.append(
            {
                "course_id": course.id,
                "course_name": getattr(course, "course_name", None) or "—",
                "teacher_name": teacher_name,
                "status": getattr(course, "status", None) or "draft",
                "created_at": (
                    course.created_at.strftime("%Y-%m-%d %H:%M")
                    if getattr(course, "created_at", None)
                    else None
                ),
            }
        )

    return results


@dashboard_router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(
    request: Request,
    format: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    Admin dashboard:
    - Web: render template
    - API: trả JSON nếu ?format=json hoặc Accept: application/json
    """

    user_role = request.session.get("role")
    username = request.session.get("username")
    is_json = wants_json(request, format)

    # ===========================
    # AUTH CHECK
    # ===========================
    if not user_role:
        if is_json:
            return JSONResponse(
                {"error": "Unauthorized", "message": "No session provided"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return RedirectResponse(
            url="/auth/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if user_role != "admin":
        if is_json:
            return JSONResponse(
                {"error": "Forbidden", "message": "Admin only"},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập trang này.",
        )

    # ===========================
    # LOAD REAL DATA
    # ===========================
    try:
        stats = build_dashboard_stats(db)
        courses = get_recent_courses(db, limit=5)
    except Exception as e:
        if is_json:
            return JSONResponse(
                {"error": "Internal Server Error", "message": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tải dữ liệu dashboard: {str(e)}",
        ) from e

    # ===========================
    # JSON RESPONSE
    # ===========================
    if is_json:
        return JSONResponse(
            {
                "status": "success",
                "username": username,
                "stats": stats,
                "courses": courses,
            }
        )

    # ===========================
    # TEMPLATE RESPONSE
    # ===========================
    templates = get_template_by_path(request.url.path)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "username": username,
            "active_page": "dashboard",
            "current_year": datetime.now().year,
            "stats": stats,
            "courses": courses,
        },
    )