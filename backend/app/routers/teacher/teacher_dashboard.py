"""
==========================================================
🎓 ROUTER: Teacher - Dashboard
Trang tổng quan dành cho giáo viên:
- Thống kê khóa học, học viên, bài tập, phản hồi
- Biểu đồ tiến độ khóa học
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from starlette import status

# ======================================================
# ✅ IMPORT CẤU HÌNH & DATABASE
# ======================================================
from app.database.connection import get_db
from app.config.template_config import templates
from app.config.paths import PUBLIC_PATH

# ✅ IMPORT MODEL
from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.assignment import Assignment
from app.models.course_review import CourseReview
from app.models.enrollment import Enrollment

# ======================================================
# ⚙️ ROUTER
# ======================================================
router = APIRouter(
    prefix="/teacher",
    tags=["Teacher - Dashboard"]
)

# ======================================================
# 🏠 DASHBOARD GIÁO VIÊN
# ======================================================
@router.get("/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Trang tổng quan dành cho giáo viên:
    - Thống kê tổng số khóa học, học viên, bài tập, phản hồi
    - Biểu đồ tiến độ khóa học (Chart.js)
    - Danh sách khóa học của giáo viên
    """

    # 🔹 Kiểm tra đăng nhập
    username = request.session.get("username")
    role = request.session.get("role")

    if not username or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    # 🔍 Lấy thông tin giáo viên
    teacher = db.query(User).filter(User.username == username).first()
    if not teacher:
        return HTMLResponse("<h3>❌ Không tìm thấy tài khoản giáo viên.</h3>", status_code=404)

    # ======================================================
    # 🧩 Lưu thông tin avatar và tên vào session
    # ======================================================
    request.session["user_avatar"] = teacher.avatar_url or f"{PUBLIC_PATH}/avatars/default-avatar.png"
    request.session["user_full_name"] = teacher.full_name

    # ======================================================
    # 📊 Thống kê tổng quan
    # ======================================================
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    total_courses = len(courses)

    total_students = (
        db.query(Enrollment)
        .join(Course, Course.id == Enrollment.course_id)
        .filter(Course.teacher_id == teacher.id)
        .count()
    )

    total_assignments = (
        db.query(Assignment)
        .join(Course, Assignment.course_id == Course.id)
        .filter(Course.teacher_id == teacher.id)
        .count()
    )

    total_feedbacks = (
        db.query(CourseReview)
        .join(Course, Course.id == CourseReview.course_id)
        .filter(Course.teacher_id == teacher.id)
        .count()
    )

    # ======================================================
    # 📈 Chuẩn bị dữ liệu biểu đồ (Chart.js)
    # ======================================================
    chart_data = []
    for c in courses:
        module_count = db.query(Module).filter(Module.course_id == c.id).count()
        lesson_count = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .filter(Module.course_id == c.id)
            .count()
        )

        # ✅ Tính tiến độ trung bình (ước lượng)
        enrolled_students = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        progress_percent = 0

        if enrolled_students > 0 and module_count > 0:
            # Tính tương đối: mỗi module giả định ~5 bài
            progress_percent = round((lesson_count / (module_count * 5)) * 100, 1)
            progress_percent = min(progress_percent, 100)

        chart_data.append({
            "course_name": c.course_name,
            "progress_percent": progress_percent
        })

    # ======================================================
    # 📦 Chuẩn bị danh sách hiển thị khóa học
    # ======================================================
    courses_display = []
    for c in courses:
        total_students_in_course = db.query(Enrollment).filter(Enrollment.course_id == c.id).count()
        progress = next((cd["progress_percent"] for cd in chart_data if cd["course_name"] == c.course_name), 0)

        courses_display.append({
            "course_name": c.course_name,
            "thumbnail_url": c.thumbnail_url or f"{PUBLIC_PATH}/course_thumbnails/default-course.png",
            "total_students": total_students_in_course,
            "progress_percent": progress
        })

    # 🧩 Log debug
    print(f"📊 [DASHBOARD] GV: {teacher.full_name} | "
          f"{total_courses} khóa học | {total_students} học viên | "
          f"{total_assignments} bài tập | {total_feedbacks} phản hồi")
    print(f"🧠 Avatar session: {request.session.get('user_avatar')}")

    # ======================================================
    # 🧾 Render Template
    # ======================================================
    return templates["teacher"].TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses_display,
            "total_courses": total_courses,
            "total_students": total_students,
            "total_assignments": total_assignments,
            "total_feedbacks": total_feedbacks,
            "chart_data": chart_data,
            "now": datetime.utcnow() + timedelta(hours=7),
        },
    )
