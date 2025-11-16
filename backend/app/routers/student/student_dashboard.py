"""
==========================================================
🎓 ROUTER: Student - Dashboard (100% Completed Edition)
==========================================================
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

# Templates
from app.config.template_config import templates

# Database & models
from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.enrollment import Enrollment
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz_attempt import QuizAttempt
from app.models.notification import Notification       # NEW
from app.models.ai_chat_history import AIChatHistory      # NEW


router = APIRouter(prefix="/student", tags=["Student - Dashboard"])


# ======================================================
# 🎓 STUDENT DASHBOARD (FULL VERSION)
# ======================================================
@router.get("/dashboard", response_class=HTMLResponse)
async def get_student_dashboard(request: Request, db: Session = Depends(get_db)):

    # 1. Kiểm tra login
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_303_SEE_OTHER)

    if role != "student":
        request.session.clear()
        return RedirectResponse("/auth/login", status.HTTP_303_SEE_OTHER)

    # 2. Lấy thông tin user
    student = db.query(User).filter(User.id == user_id).first()
    if not student:
        return RedirectResponse("/auth/login", status.HTTP_303_SEE_OTHER)

    try:
        # ======================================================
        # 📘 1) Lấy danh sách khóa học đã ghi danh (2 mô hình)
        # ======================================================
        enrolled_courses = (
            db.query(Course)
            .join(Module, Module.course_id == Course.id)
            .join(Lesson, Lesson.module_id == Module.id)
            .join(Enrollment, (Enrollment.course_id == Course.id) | (Enrollment.class_id != None))
            .filter(Enrollment.user_id == student.id)
            .group_by(Course.id)
            .all()
        )

        # ======================================================
        # 📊 2) Tổng tiến độ học tập
        # ======================================================
        total_lessons = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == student.id)
            .count()
        )

        completed_lessons = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == student.id,
                LessonProgress.progress_status == "completed",
            )
            .count()
        )

        in_progress_lessons = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == student.id,
                LessonProgress.progress_status == "in_progress",
            )
            .count()
        )

        progress_percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0

        progress_stats = {
            "completed": completed_lessons,
            "in_progress": in_progress_lessons,
            "total": total_lessons,
            "percent": progress_percent,
        }

        # ======================================================
        # 📘 3) Tiến độ từng khóa học (progress bar)
        # ======================================================
        course_progress_list = []

        for c in enrolled_courses:
            total_lesson_c = (
                db.query(func.count(Lesson.id))
                .join(Module, Lesson.module_id == Module.id)
                .filter(Module.course_id == c.id)
                .scalar()
            )

            completed_c = (
                db.query(func.count(LessonProgress.id))
                .join(Lesson, LessonProgress.lesson_id == Lesson.id)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    LessonProgress.user_id == student.id,
                    LessonProgress.progress_status == "completed",
                    Module.course_id == c.id,
                )
                .scalar()
            )

            percent_c = round((completed_c / total_lesson_c) * 100, 1) if total_lesson_c else 0

            course_progress_list.append({
                "course": c,
                "completed": completed_c,
                "total": total_lesson_c,
                "percent": percent_c,
            })

        # ======================================================
        # 📝 4) Bài tập đã nộp
        # ======================================================
        total_assignments = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.student_id == student.id)
            .count()
        )

        # ======================================================
        # ❓ 5) Quiz đã làm
        # ======================================================
        total_quizzes = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == student.id)
            .count()
        )

        # ======================================================
        # 🕒 6) Bài học gần đây
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
        # 🔔 7) Thông báo thật từ DB
        # ======================================================
        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == student.id)
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all()
        )

        unread_notifications = (
            db.query(func.count(Notification.id))
            .filter(Notification.user_id == student.id, Notification.is_read == 0)
            .scalar()
        )

        # ======================================================
        # 🤖 8) AI Chat History (optional stats)
        # ======================================================
        last_chat = (
            db.query(AIChatHistory)
            .filter(AIChatHistory.user_id == student.id)
            .order_by(AIChatHistory.created_at.desc())
            .first()
        )

        total_ai_messages = (
            db.query(func.count(AIChatHistory.id))
            .filter(AIChatHistory.user_id == student.id)
            .scalar()
        )

        # ======================================================
        # 🖼️ 9) Avatar
        # ======================================================
        avatar_url = (
            request.session.get("user_avatar")
            or student.avatar_url
            or "/static/img/default_avatar.png"
        )

        # ======================================================
        # 🧾 Render dashboard
        # ======================================================
        return templates["student"].TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": student,
                "avatar_url": avatar_url,
                "enrolled_courses": enrolled_courses,

                "progress_stats": progress_stats,
                "course_progress_list": course_progress_list,

                "recent_lessons": recent_lessons,

                "notifications": notifications,
                "unread_notifications": unread_notifications,

                "total_assignments": total_assignments,
                "total_quizzes": total_quizzes,

                "last_chat": last_chat,
                "total_ai_messages": total_ai_messages,

                "active_page": "dashboard",
                "now": datetime.utcnow() + timedelta(hours=7),
            },
        )

    except Exception as e:
        print("💥 DASHBOARD ERROR:", e)
        return templates["student"].TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Lỗi tải dashboard: {e}",
                "now": datetime.utcnow() + timedelta(hours=7),
            },
        )
