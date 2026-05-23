import traceback
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config.template_config import templates
from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.course_enrollment import CourseEnrollment
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz_attempt import QuizAttempt
from app.models.notification import Notification
from app.models.ai_chat_history import AIChatHistory
from app.services.student.dashboard_service import get_continue_learning, get_dashboard_todo_summary

router = APIRouter(prefix="/student", tags=["Student - Dashboard"])


def get_current_student(request: Request, db: Session):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "student":
        return None
    return db.query(User).filter(User.id == user_id).first()


@router.get("/dashboard", response_class=HTMLResponse)
async def get_student_dashboard(request: Request, db: Session = Depends(get_db)):
    student = get_current_student(request, db)
    if not student:
        request.session.clear()
        return RedirectResponse("/auth/login", status_code=303)

    try:
        active_enrollments = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == student.id,
                CourseEnrollment.course_id.isnot(None),
                CourseEnrollment.enrollment_status.in_(["approved", "active", "completed"]),
            )
            .all()
        )
        course_ids = [e.course_id for e in active_enrollments if e.course_id]

        enrolled_courses = []
        if course_ids:
            enrolled_courses = db.query(Course).filter(Course.id.in_(course_ids)).all()

        total_lessons = 0
        if course_ids:
            total_lessons = (
                db.query(func.count(Lesson.id))
                .join(Module, Lesson.module_id == Module.id)
                .filter(Module.course_id.in_(course_ids))
                .scalar()
                or 0
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

        course_progress_list = []
        for c in enrolled_courses:
            total_lesson_c = (
                db.query(func.count(Lesson.id))
                .join(Module, Lesson.module_id == Module.id)
                .filter(Module.course_id == c.id)
                .scalar()
                or 0
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
                or 0
            )

            percent_c = round((completed_c / total_lesson_c) * 100, 1) if total_lesson_c else 0

            course_progress_list.append(
                {
                    "course": c,
                    "completed": completed_c,
                    "total": total_lesson_c,
                    "percent": percent_c,
                }
            )

        total_assignments = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.student_id == student.id)
            .count()
        )

        total_quizzes = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == student.id)
            .count()
        )

        recent_lessons = []
        if course_ids:
            recent_lessons = (
                db.query(Lesson)
                .join(Module, Lesson.module_id == Module.id)
                .filter(Module.course_id.in_(course_ids))
                .order_by(Lesson.created_at.desc())
                .limit(5)
                .all()
            )

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
            or 0
        )

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
            or 0
        )

        avatar_url = (
            request.session.get("user_avatar")
            or getattr(student, "avatar_url", None)
            or "/static/img/default_avatar.png"
        )

        continue_learning = get_continue_learning(db, student.id)
        todo_summary = get_dashboard_todo_summary(db, student.id)

        return templates["student"].TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": student,
                "avatar_url": avatar_url,
                "enrolled_courses": enrolled_courses,
                "progress_stats": progress_stats,
                "course_progress_list": course_progress_list,
                "continue_learning": continue_learning,
                "todo_summary": todo_summary,
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
        traceback.print_exc()
        return templates["student"].TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Lỗi tải dashboard: {e}",
                "now": datetime.utcnow() + timedelta(hours=7),
            },
            status_code=500,
        )
