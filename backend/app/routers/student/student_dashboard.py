"""
==========================================================
🎓 ROUTER: Student - Dashboard
Hiển thị bảng điều khiển chính của sinh viên:
- Khóa học đã ghi danh
- Tiến độ học tập
- Bài học gần đây
- Thông báo
==========================================================
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# ✅ Import cấu hình template
from app.config.template_config import templates

# ✅ Import database & models
from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.enrollment import Enrollment
from app.models.lesson_progress import LessonProgress
from app.models.lesson import Lesson
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz_attempt import QuizAttempt


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(prefix="/student", tags=["Student - Dashboard"])


# ======================================================
# 🎓 Trang Dashboard Sinh viên
# ======================================================
@router.get("/dashboard", response_class=HTMLResponse)
async def get_student_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị bảng điều khiển chính của sinh viên:
    - Các khóa học đã ghi danh
    - Tiến độ học tập
    - Bài học gần đây
    - Thông báo
    """

    # 🧩 Kiểm tra đăng nhập
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    # 🚫 Nếu chưa login → redirect về trang login
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    # 🚫 Nếu role khác student → logout
    if role != "student":
        request.session.clear()
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    # 🔹 Lấy thông tin sinh viên
    student = db.query(User).filter(User.id == user_id).first()
    if not student:
        request.session.clear()
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        # ======================================================
        # 📘 1️⃣ Lấy danh sách khóa học sinh viên đã ghi danh
        # ======================================================
        enrolled_courses = (
            db.query(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == student.id)
            .all()
        )

        # ======================================================
        # 📊 2️⃣ Tiến độ học tập
        # ======================================================
        completed_lessons = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == student.id,
                LessonProgress.progress_status == "completed",
            )
            .count()
        )

        total_lessons = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == student.id)
            .count()
        )

        progress_percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons > 0 else 0

        progress_stats = {
            "completed": completed_lessons,
            "total": total_lessons,
            "percent": progress_percent,
        }

        # ======================================================
        # 📝 3️⃣ Tổng số bài tập đã nộp
        # ======================================================
        total_assignments = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.student_id == student.id)
            .count()
        )

        # ======================================================
        # 🧠 4️⃣ Tổng số quiz đã làm
        # ======================================================
        total_quizzes = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == student.id)
            .count()
        )

        # ======================================================
        # 🕒 5️⃣ Bài học gần đây
        # ======================================================
        recent_lessons = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == student.id)
            .order_by(Lesson.created_at.desc())
            .limit(5)
            .all()
        )

        # ======================================================
        # 🔔 6️⃣ Dummy Thông báo
        # ======================================================
        notifications = [
            {"icon": "bi bi-bell-fill text-warning", "text": "📘 Bạn có bài tập mới cần nộp trong tuần này."},
            {"icon": "bi bi-award text-success", "text": "🏆 Khóa học Python cơ bản của bạn đã đạt 80% tiến độ."},
            {"icon": "bi bi-chat-dots text-info", "text": "💬 Giảng viên đã phản hồi bình luận của bạn."},
        ]

        # ======================================================
        # 🖼️ 7️⃣ Lấy avatar (ưu tiên từ session)
        # ======================================================
        avatar_url = (
            request.session.get("user_avatar")
            or student.avatar_url
            or "/static/img/default_avatar.png"
        )

        # 🧾 Log debug
        print(
            f"📊 [STUDENT DASHBOARD] {student.full_name} — "
            f"{len(enrolled_courses)} khóa học, "
            f"{completed_lessons}/{total_lessons} bài học ({progress_percent}%)"
        )

        # ======================================================
        # 🧾 8️⃣ Render template
        # ======================================================
        return templates["student"].TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": student,  # ✅ Dùng cho layout_student.html
                "avatar_url": avatar_url,
                "enrolled_courses": enrolled_courses,
                "progress_stats": progress_stats,
                "recent_lessons": recent_lessons,
                "notifications": notifications,
                "total_assignments": total_assignments,
                "total_quizzes": total_quizzes,
                "active_page": "dashboard",
                "now": datetime.utcnow() + timedelta(hours=7),
            },
        )

    except Exception as e:
        print(f"💥 [ERROR] Lỗi khi tải dashboard sinh viên: {e}")
        return templates["student"].TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Không thể tải trang Dashboard. Chi tiết lỗi: {e}",
                "now": datetime.utcnow() + timedelta(hours=7),
            },
        )
