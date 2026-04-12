from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.quiz import Quiz
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.course_review import CourseReview


ACTIVE_ENROLLMENT_STATUSES = {"approved", "active", "completed"}


def get_course_overview(db: Session, course_id: str):
    """
    Tổng hợp overview của 1 khóa học:
    - số module
    - số lesson
    - số quiz
    - số assignment
    - số học viên đang tham gia
    - điểm rating trung bình
    """

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Không tìm thấy khóa học.")

    total_modules = (
        db.query(func.count(Module.id))
        .filter(Module.course_id == course_id)
        .scalar()
        or 0
    )

    total_lessons = (
        db.query(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course_id)
        .scalar()
        or 0
    )

    total_quizzes = (
        db.query(func.count(Quiz.id))
        .filter(Quiz.course_id == course_id)
        .scalar()
        or 0
    )

    total_assignments = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.course_id == course_id)
        .scalar()
        or 0
    )

    total_students = (
        db.query(func.count(distinct(Enrollment.student_id)))
        .filter(Enrollment.course_id == course_id)
        .filter(Enrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .scalar()
        or 0
    )

    avg_rating = (
        db.query(func.avg(CourseReview.overall_rating))
        .filter(CourseReview.course_id == course_id)
        .scalar()
    )

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