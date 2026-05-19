from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.course_review import CourseReview
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.quiz import Quiz


ACTIVE_ENROLLMENT_STATUSES = {"approved", "active", "completed"}


def get_course_overview(db: Session, course_id: str | None = None):
    """
    Thống kê khóa học.
    - Nếu có course_id: trả overview của 1 khóa học.
    - Nếu không có course_id: trả thống kê tổng quan toàn hệ thống cho dashboard admin.
    """
    if course_id is None:
        total_courses = db.query(func.count(Course.id)).filter(Course.deleted_at.is_(None)).scalar() or 0
        published_courses = (
            db.query(func.count(Course.id))
            .filter(Course.deleted_at.is_(None), Course.status == "published")
            .scalar()
            or 0
        )
        draft_courses = (
            db.query(func.count(Course.id))
            .filter(Course.deleted_at.is_(None), Course.status == "draft")
            .scalar()
            or 0
        )
        archived_courses = (
            db.query(func.count(Course.id))
            .filter(Course.deleted_at.is_(None), Course.status == "archived")
            .scalar()
            or 0
        )
        total_modules = db.query(func.count(Module.id)).scalar() or 0
        total_lessons = db.query(func.count(Lesson.id)).filter(Lesson.deleted_at.is_(None)).scalar() or 0
        total_quizzes = db.query(func.count(Quiz.id)).scalar() or 0
        total_assignments = db.query(func.count(Assignment.id)).scalar() or 0
        total_students = (
            db.query(func.count(distinct(CourseEnrollment.user_id)))
            .filter(CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
            .scalar()
            or 0
        )
        avg_rating = db.query(func.avg(CourseReview.overall_rating)).scalar() or 0

        return {
            "total_courses": int(total_courses),
            "published_courses": int(published_courses),
            "draft_courses": int(draft_courses),
            "archived_courses": int(archived_courses),
            "total_modules": int(total_modules),
            "total_lessons": int(total_lessons),
            "total_quizzes": int(total_quizzes),
            "total_assignments": int(total_assignments),
            "active_students": int(total_students),
            "avg_rating": round(float(avg_rating or 0), 2),
        }

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Không tìm thấy khóa học.")

    total_modules = db.query(func.count(Module.id)).filter(Module.course_id == course_id).scalar() or 0
    total_lessons = (
        db.query(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course_id, Lesson.deleted_at.is_(None))
        .scalar()
        or 0
    )
    total_quizzes = db.query(func.count(Quiz.id)).filter(Quiz.course_id == course_id).scalar() or 0
    total_assignments = db.query(func.count(Assignment.id)).filter(Assignment.course_id == course_id).scalar() or 0
    total_students = (
        db.query(func.count(distinct(CourseEnrollment.user_id)))
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .scalar()
        or 0
    )
    avg_rating = db.query(func.avg(CourseReview.overall_rating)).filter(CourseReview.course_id == course_id).scalar()

    return {
        "course_id": course.id,
        "course_code": getattr(course, "course_code", None),
        "course_name": getattr(course, "course_name", None),
        "modules": int(total_modules),
        "lessons": int(total_lessons),
        "quizzes": int(total_quizzes),
        "assignments": int(total_assignments),
        "students": int(total_students),
        "avg_rating": round(float(avg_rating or 0), 2),
    }
