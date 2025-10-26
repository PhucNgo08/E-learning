"""
==========================================================
📊 SERVICE: Teacher - Statistics
Thống kê tổng quan cho giáo viên
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.assignment import Assignment
from app.models.enrollment import Enrollment
from app.models.course_review import CourseReview


# ======================================================
# 📈 1️⃣ Thống kê tổng quan cho giáo viên
# ======================================================
def get_teacher_statistics(db: Session, teacher_id: str):
    """Trả về thống kê tổng quan cho giáo viên"""

    # 🔹 Tổng số khóa học
    total_courses = db.query(Course).filter(Course.teacher_id == teacher_id).count()

    # 🔹 Tổng số module
    total_modules = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .count()
    )

    # 🔹 Tổng số bài học (join qua Module → Course)
    total_lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .count()
    )

    # 🔹 Tổng số bài tập
    total_assignments = (
        db.query(Assignment)
        .filter(Assignment.teacher_id == teacher_id)
        .count()
    )

    # 🔹 Tổng số học viên trong các khóa của giáo viên
    total_students = (
        db.query(Enrollment)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .count()
    )

    # 🔹 Điểm trung bình đánh giá khóa học
    avg_rating = (
        db.query(func.avg(CourseReview.overall_rating))
        .join(Course, CourseReview.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .scalar()
    )

    # 🔹 Top 3 khóa học được đánh giá cao nhất
    top_courses = (
        db.query(
            Course.course_name,
            func.avg(CourseReview.overall_rating).label("avg_rating"),
            func.count(CourseReview.id).label("total_reviews"),
        )
        .join(CourseReview, CourseReview.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .group_by(Course.id)
        .order_by(func.avg(CourseReview.overall_rating).desc())
        .limit(3)
        .all()
    )

    return {
        "total_courses": total_courses,
        "total_modules": total_modules,
        "total_lessons": total_lessons,
        "total_assignments": total_assignments,
        "total_students": total_students,
        "average_rating": round(float(avg_rating or 0), 2),
        "top_courses": [
            {
                "name": c.course_name,
                "avg_rating": round(float(c.avg_rating or 0), 2),
                "total_reviews": c.total_reviews,
            }
            for c in top_courses
        ],
    }
