from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.class_enrollment import ClassEnrollment
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.quiz import Quiz
from app.models.user import User
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.course_review import CourseReview
from app.models.quiz_attempt import QuizAttempt
from app.models.lesson_progress import LessonProgress
from app.models.rbac import Role

ACTIVE_CLASS_ENROLLMENT_STATUSES = {"active", "approved"}
ACTIVE_COURSE_ENROLLMENT_STATUSES = {"active", "approved", "completed"}

SUPPORTED_REPORT_TYPES = {
    "overview",
    "class_enrollments",
    "course_enrollments",
    "recent_activity",
}


def get_dashboard_stats(db: Session):
    total_students = (
        db.query(func.count(User.id))
        .join(User.roles)
        .filter(Role.role_code == "student")
        .scalar() or 0
    )

    total_teachers = (
        db.query(func.count(User.id))
        .join(User.roles)
        .filter(Role.role_code == "teacher")
        .scalar() or 0
    )

    total_courses = db.query(func.count(Course.id)).scalar() or 0
    total_modules = db.query(func.count(Module.id)).scalar() or 0
    total_lessons = db.query(func.count(Lesson.id)).scalar() or 0
    total_reviews = db.query(func.count(CourseReview.id)).scalar() or 0

    # sửa chỗ này: đếm số bài quiz, không đếm số lượt attempt
    total_quizzes = db.query(func.count(Quiz.id)).scalar() or 0

    completed_lessons = (
        db.query(func.count(LessonProgress.id))
        .filter(LessonProgress.progress_status == "completed")
        .scalar() or 0
    )

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_courses": total_courses,
        "total_modules": total_modules,
        "total_lessons": total_lessons,
        "total_reviews": total_reviews,
        "total_quizzes": total_quizzes,
        "completed_lessons": completed_lessons,
    }


def generate_report(db: Session, report_type: str = "overview"):
    report_type = (report_type or "overview").strip().lower()

    if report_type not in SUPPORTED_REPORT_TYPES:
        raise ValueError(f"Loại báo cáo không hợp lệ: {report_type}")

    if report_type == "overview":
        return {
            "report_type": "overview",
            "generated_at": datetime.utcnow().isoformat(),
            "data": get_dashboard_stats(db),
        }

    if report_type == "class_enrollments":
        rows = (
            db.query(
                Class.id,
                Class.class_code,
                Class.class_name,
                func.count(ClassEnrollment.id).label("student_count"),
            )
            .outerjoin(
                ClassEnrollment,
                (ClassEnrollment.class_id == Class.id)
                & (ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES)),
            )
            .group_by(Class.id, Class.class_code, Class.class_name)
            .order_by(Class.created_at.desc())
            .all()
        )

        return {
            "report_type": "class_enrollments",
            "generated_at": datetime.utcnow().isoformat(),
            "data": [
                {
                    "class_id": row.id,
                    "class_code": row.class_code,
                    "class_name": row.class_name,
                    "student_count": int(row.student_count or 0),
                }
                for row in rows
            ],
        }

    if report_type == "course_enrollments":
        rows = (
            db.query(
                Course.id,
                Course.course_code,
                Course.course_name,
                func.count(CourseEnrollment.id).label("student_count"),
            )
            .outerjoin(
                CourseEnrollment,
                (CourseEnrollment.course_id == Course.id)
                & (CourseEnrollment.enrollment_status.in_(ACTIVE_COURSE_ENROLLMENT_STATUSES)),
            )
            .group_by(Course.id, Course.course_code, Course.course_name)
            .order_by(Course.created_at.desc())
            .all()
        )

        return {
            "report_type": "course_enrollments",
            "generated_at": datetime.utcnow().isoformat(),
            "data": [
                {
                    "course_id": row.id,
                    "course_code": row.course_code,
                    "course_name": row.course_name,
                    "student_count": int(row.student_count or 0),
                }
                for row in rows
            ],
        }

    if report_type == "recent_activity":
        since = datetime.utcnow() - timedelta(days=30)

        recent_users = db.query(func.count(User.id)).filter(User.created_at >= since).scalar() or 0
        recent_courses = db.query(func.count(Course.id)).filter(Course.created_at >= since).scalar() or 0
        recent_classes = db.query(func.count(Class.id)).filter(Class.created_at >= since).scalar() or 0

        return {
            "report_type": "recent_activity",
            "generated_at": datetime.utcnow().isoformat(),
            "data": {
                "new_users_last_30_days": recent_users,
                "new_courses_last_30_days": recent_courses,
                "new_classes_last_30_days": recent_classes,
            },
        }