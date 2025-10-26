from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.quiz import Quiz
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.course_review import CourseReview

def get_course_overview(db: Session, course_id: str):
    """Tổng hợp số lượng thành phần của 1 khóa học"""
    total_modules = db.query(func.count(Module.id)).filter(Module.course_id == course_id).scalar()
    total_lessons = db.query(func.count(Lesson.id)).join(Module).filter(Module.course_id == course_id).scalar()
    total_quizzes = db.query(func.count(Quiz.id)).filter(Quiz.course_id == course_id).scalar()
    total_assignments = db.query(func.count(Assignment.id)).filter(Assignment.course_id == course_id).scalar()
    total_students = db.query(func.count(Enrollment.id)).filter(Enrollment.course_id == course_id).scalar()

    avg_rating = db.query(func.avg(CourseReview.overall_rating)).filter(CourseReview.course_id == course_id).scalar() or 0

    return {
        "modules": total_modules,
        "lessons": total_lessons,
        "quizzes": total_quizzes,
        "assignments": total_assignments,
        "students": total_students,
        "avg_rating": round(avg_rating, 2)
    }
