from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.course_review import CourseReview
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.quiz import Quiz


ACTIVE_ENROLLMENT_STATUSES = {"approved", "active", "completed"}


def _apply_not_deleted(query, model):
    if hasattr(model, "deleted_at"):
        return query.filter(model.deleted_at.is_(None))
    return query


def get_course_overview(db: Session, course_id: str | None = None):
    """
    Nếu truyền course_id: trả overview 1 khóa học.
    Nếu không truyền course_id: trả dashboard tổng quan toàn hệ thống cho Admin.
    """
    if course_id:
        return get_single_course_overview(db, course_id)
    return get_all_courses_overview(db)


def get_all_courses_overview(db: Session):
    course_query = db.query(Course)
    course_query = _apply_not_deleted(course_query, Course)

    total_courses = course_query.count()
    published_courses = course_query.filter(Course.status == "published").count()
    draft_courses = course_query.filter(Course.status == "draft").count()
    archived_courses = course_query.filter(Course.status == "archived").count()

    total_modules_q = db.query(func.count(Module.id))
    total_modules_q = _apply_not_deleted(total_modules_q, Module)

    total_lessons_q = db.query(func.count(Lesson.id)).join(Module, Lesson.module_id == Module.id)
    total_lessons_q = _apply_not_deleted(total_lessons_q, Lesson)
    total_lessons_q = _apply_not_deleted(total_lessons_q, Module)

    published_lessons_q = total_lessons_q.filter(Lesson.is_published == 1)

    total_students = (
        db.query(func.count(distinct(CourseEnrollment.user_id)))
        .filter(CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .scalar()
        or 0
    )

    total_enrollments = (
        db.query(func.count(CourseEnrollment.id))
        .filter(CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .scalar()
        or 0
    )

    total_assignments = db.query(func.count(Assignment.id)).scalar() or 0
    total_quizzes = db.query(func.count(Quiz.id)).scalar() or 0
    avg_rating = db.query(func.avg(CourseReview.overall_rating)).scalar() or 0

    return {
        "total_courses": int(total_courses or 0),
        "published_courses": int(published_courses or 0),
        "draft_courses": int(draft_courses or 0),
        "archived_courses": int(archived_courses or 0),
        "total_modules": int(total_modules_q.scalar() or 0),
        "total_lessons": int(total_lessons_q.scalar() or 0),
        "published_lessons": int(published_lessons_q.scalar() or 0),
        "total_students": int(total_students),
        "total_enrollments": int(total_enrollments),
        "total_assignments": int(total_assignments),
        "total_quizzes": int(total_quizzes),
        "avg_rating": round(float(avg_rating), 2),
    }


def get_single_course_overview(db: Session, course_id: str):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Không tìm thấy khóa học.")

    module_q = db.query(func.count(Module.id)).filter(Module.course_id == course_id)
    module_q = _apply_not_deleted(module_q, Module)

    lesson_q = (
        db.query(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course_id)
    )
    lesson_q = _apply_not_deleted(lesson_q, Lesson)
    lesson_q = _apply_not_deleted(lesson_q, Module)

    total_students = (
        db.query(func.count(distinct(CourseEnrollment.user_id)))
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .scalar()
        or 0
    )

    avg_rating = (
        db.query(func.avg(CourseReview.overall_rating))
        .filter(CourseReview.course_id == course_id)
        .scalar()
        or 0
    )

    return {
        "course_id": course.id,
        "course_code": getattr(course, "course_code", None),
        "course_name": getattr(course, "course_name", None),
        "modules": int(module_q.scalar() or 0),
        "lessons": int(lesson_q.scalar() or 0),
        "quizzes": int(db.query(func.count(Quiz.id)).filter(Quiz.course_id == course_id).scalar() or 0),
        "assignments": int(db.query(func.count(Assignment.id)).filter(Assignment.course_id == course_id).scalar() or 0),
        "students": int(total_students),
        "avg_rating": round(float(avg_rating), 2),
    }
