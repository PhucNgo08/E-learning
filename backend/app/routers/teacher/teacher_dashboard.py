from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.course_review import CourseReview
from datetime import datetime

# ============================================================
# 🧭 Cấu hình Template (trỏ đến thư mục /templates cha)
# ============================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ============================================================
# 🚀 Khởi tạo Router
# ============================================================
router = APIRouter(
    prefix="/teacher",
    tags=["Teacher Dashboard"]
)

# ============================================================
# 📊 Trang Dashboard Giáo viên
# ============================================================
@router.get("/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Trang tổng quan của giáo viên — hiển thị thống kê khóa học, bài học, đánh giá.
    """

    # ✅ Lấy thông tin từ session
    user_id = request.session.get("user_id")
    user_role = request.session.get("role")

    # ✅ Kiểm tra quyền truy cập
    if not user_id or user_role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    # ✅ Lấy thông tin giáo viên hiện tại
    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return templates.TemplateResponse(
            "teacher/dashboard.html",
            {"request": request, "error": "Không tìm thấy giáo viên!"}
        )

    # ============================================================
    # 📚 Thống kê cơ bản
    # ============================================================
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    total_courses = len(courses)

    total_lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher.id)
        .count()
    )

    total_reviews = (
        db.query(CourseReview)
        .join(Course, Course.id == CourseReview.course_id)
        .filter(Course.teacher_id == teacher.id)
        .count()
    )

    # ============================================================
    # 🕒 Dữ liệu hiển thị
    # ============================================================
    recent_courses = (
        db.query(Course)
        .filter(Course.teacher_id == teacher.id)
        .order_by(Course.created_at.desc())
        .limit(5)
        .all()
    )

    recent_reviews = (
        db.query(CourseReview)
        .join(Course, Course.id == CourseReview.course_id)
        .filter(Course.teacher_id == teacher.id)
        .order_by(CourseReview.created_at.desc())
        .limit(5)
        .all()
    )

    # ============================================================
    # 📈 Dữ liệu cho biểu đồ Chart.js
    # ============================================================
    courses_json = [
        {
            "course_name": c.course_name,
            "course_code": c.course_code,
            "status": c.status,
            "lesson_count": len(c.modules) if hasattr(c, "modules") else 0,
            "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else None,
        }
        for c in recent_courses
    ]

    # ============================================================
    # 🧾 Render Template
    # ============================================================
    return templates.TemplateResponse(
        "teacher/dashboard.html",
        {
            "request": request,
            "teacher": teacher,
            "total_courses": total_courses,
            "total_lessons": total_lessons,
            "total_reviews": total_reviews,
            "recent_courses": recent_courses,
            "recent_reviews": recent_reviews,
            "courses_json": courses_json,
            "now": datetime.now(),
        },
    )
