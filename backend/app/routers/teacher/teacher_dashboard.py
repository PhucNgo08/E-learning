from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette import status

from app.database.connection import get_db
from app.config.template_config import templates
from app.config.paths import PUBLIC_PATH

from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.assignment import Assignment
from app.models.course_review import CourseReview
from app.models.class_enrollment import ClassEnrollment
from app.models.course_enrollment import CourseEnrollment
from app.models.lesson_progress import LessonProgress


router = APIRouter(
    prefix="/teacher",
    tags=["Teacher - Dashboard"]
)


VALID_ENROLLMENT_STATUSES = ["approved", "active", "completed"]


def get_current_teacher(request: Request, db: Session):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return None

    return db.query(User).filter(User.id == user_id).first()


@router.get("/dashboard", response_class=HTMLResponse)
def teacher_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        teacher = get_current_teacher(request, db)
        if not teacher:
            return RedirectResponse(
                url="/auth/login",
                status_code=status.HTTP_303_SEE_OTHER
            )

        request.session["user_avatar"] = (
            getattr(teacher, "avatar_url", None)
            or f"{PUBLIC_PATH}/avatars/default-avatar.png"
        )
        request.session["user_full_name"] = (
            getattr(teacher, "full_name", None)
            or getattr(teacher, "username", "Teacher")
        )

        courses = (
            db.query(Course)
            .filter(Course.teacher_id == teacher.id)
            .order_by(Course.created_at.desc())
            .all()
        )

        course_ids = [c.id for c in courses]
        total_courses = len(courses)

        total_students = 0
        total_assignments = 0
        total_feedbacks = 0

        if course_ids:
            total_students = (
                db.query(func.count(func.distinct(CourseEnrollment.user_id)))
                .filter(
                    CourseEnrollment.course_id.in_(course_ids),
                    CourseEnrollment.enrollment_status.in_(VALID_ENROLLMENT_STATUSES),
                )
                .scalar()
                or 0
            )

            total_assignments = (
                db.query(func.count(Assignment.id))
                .filter(Assignment.course_id.in_(course_ids))
                .scalar()
                or 0
            )

            total_feedbacks = (
                db.query(func.count(CourseReview.id))
                .filter(CourseReview.course_id.in_(course_ids))
                .scalar()
                or 0
            )

        chart_data = []
        courses_display = []

        for course in courses:
            total_students_in_course = (
                db.query(func.count(func.distinct(CourseEnrollment.user_id)))
                .filter(
                    CourseEnrollment.course_id == course.id,
                    CourseEnrollment.enrollment_status.in_(VALID_ENROLLMENT_STATUSES),
                )
                .scalar()
                or 0
            )

            total_lessons = (
                db.query(func.count(Lesson.id))
                .join(Module, Lesson.module_id == Module.id)
                .filter(Module.course_id == course.id)
                .scalar()
                or 0
            )

            completed_lesson_records = (
                db.query(func.count(LessonProgress.id))
                .join(Lesson, LessonProgress.lesson_id == Lesson.id)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    Module.course_id == course.id,
                    LessonProgress.progress_status == "completed",
                )
                .scalar()
                or 0
            )

            if total_students_in_course > 0 and total_lessons > 0:
                progress_percent = round(
                    (completed_lesson_records / (total_students_in_course * total_lessons)) * 100,
                    1,
                )
                progress_percent = min(progress_percent, 100.0)
            else:
                progress_percent = 0.0

            chart_data.append({
                "course_name": course.course_name,
                "progress_percent": progress_percent,
            })

            courses_display.append({
                "course_id": course.id,
                "course_name": course.course_name,
                "thumbnail_url": (
                    course.thumbnail_url
                    or f"{PUBLIC_PATH}/course_thumbnails/default-course.png"
                ),
                "total_students": total_students_in_course,
                "total_lessons": total_lessons,
                "progress_percent": progress_percent,
                "status": getattr(course, "status", None),
                "is_public": getattr(course, "is_public", None),
            })

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

    except Exception as e:
        print("TEACHER DASHBOARD ERROR:", e)
        return templates["teacher"].TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"Lỗi tải dashboard giáo viên: {e}",
                "now": datetime.utcnow() + timedelta(hours=7),
            },
            status_code=500,
        )