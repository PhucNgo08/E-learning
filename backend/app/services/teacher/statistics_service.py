"""
==========================================================
📊 SERVICE: Teacher - Statistics
Thống kê tổng quan cho giáo viên
==========================================================
"""

from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.quiz import Quiz

# Các model này có thể có hoặc không tùy project
try:
    from app.models.assignment import Assignment
except Exception:
    Assignment = None

try:
    from app.models.course_material import CourseMaterial
except Exception:
    CourseMaterial = None

try:
    from app.models.course_review import CourseReview
except Exception:
    CourseReview = None

try:
    from app.models.classes import Class
except Exception:
    Class = None

try:
    from app.models.enrollment import ClassEnrollment
except Exception:
    ClassEnrollment = None


ACTIVE_ENROLL_STATUSES = {"approved", "active", "completed"}


def _safe_count(query):
    try:
        return int(query.scalar() or 0)
    except Exception:
        return 0


def get_teacher_statistics(db: Session, teacher_id: str):
    """
    Trả về dict thống kê tổng quan cho giáo viên.
    Thiết kế theo kiểu an toàn: nếu model nào không tồn tại thì trả 0 ở mục tương ứng.
    """
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    tomorrow_start = today_start + timedelta(days=1)

    courses = (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.created_at.desc() if hasattr(Course, "created_at") else Course.course_name.asc())
        .all()
    )
    course_ids = [c.id for c in courses]

    data = {
        "total_courses": 0,
        "published_courses": 0,
        "draft_courses": 0,
        "archived_courses": 0,

        "total_modules": 0,
        "published_modules": 0,

        "total_lessons": 0,
        "published_lessons": 0,
        "today_lessons": 0,
        "upcoming_lessons": 0,

        "total_quizzes": 0,
        "graded_quizzes": 0,
        "practice_quizzes": 0,

        "total_assignments": 0,
        "total_materials": 0,

        "total_reviews": 0,
        "avg_rating": 0.0,
        "rating_distribution": [0, 0, 0, 0, 0],  # 1 → 5

        "total_classes": 0,
        "total_students": 0,

        "latest_courses": [],
    }

    if not course_ids:
        return data

    data["total_courses"] = len(courses)
    data["published_courses"] = sum(1 for c in courses if getattr(c, "status", None) == "published")
    data["draft_courses"] = sum(1 for c in courses if getattr(c, "status", None) == "draft")
    data["archived_courses"] = sum(1 for c in courses if getattr(c, "status", None) == "archived")

    data["latest_courses"] = [
        {
            "id": c.id,
            "course_name": getattr(c, "course_name", ""),
            "status": getattr(c, "status", ""),
            "created_at": getattr(c, "created_at", None),
        }
        for c in courses[:5]
    ]

    # ======================================================
    # Modules
    # ======================================================
    module_query = db.query(Module).filter(Module.course_id.in_(course_ids))
    if hasattr(Module, "deleted_at"):
        module_query = module_query.filter(Module.deleted_at.is_(None))

    modules = module_query.all()
    data["total_modules"] = len(modules)
    data["published_modules"] = sum(1 for m in modules if bool(getattr(m, "is_published", False)))

    # ======================================================
    # Lessons
    # ======================================================
    lesson_query = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id.in_(course_ids))
    )
    if hasattr(Module, "deleted_at"):
        lesson_query = lesson_query.filter(Module.deleted_at.is_(None))

    lessons = lesson_query.all()
    data["total_lessons"] = len(lessons)
    data["published_lessons"] = sum(1 for l in lessons if bool(getattr(l, "is_published", False)))

    if hasattr(Lesson, "start_time"):
        data["today_lessons"] = _safe_count(
            db.query(func.count(Lesson.id))
            .join(Module, Lesson.module_id == Module.id)
            .filter(
                Module.course_id.in_(course_ids),
                Lesson.start_time.isnot(None),
                Lesson.start_time >= today_start,
                Lesson.start_time < tomorrow_start,
            )
        )

        data["upcoming_lessons"] = _safe_count(
            db.query(func.count(Lesson.id))
            .join(Module, Lesson.module_id == Module.id)
            .filter(
                Module.course_id.in_(course_ids),
                Lesson.start_time.isnot(None),
                Lesson.start_time >= now,
            )
        )

    # ======================================================
    # Quizzes
    # ======================================================
    quizzes = db.query(Quiz).filter(Quiz.course_id.in_(course_ids)).all()
    data["total_quizzes"] = len(quizzes)
    data["graded_quizzes"] = sum(1 for q in quizzes if getattr(q, "quiz_type", None) == "graded")
    data["practice_quizzes"] = sum(1 for q in quizzes if getattr(q, "quiz_type", None) != "graded")

    # ======================================================
    # Assignments
    # ======================================================
    if Assignment is not None:
        data["total_assignments"] = _safe_count(
            db.query(func.count(Assignment.id))
            .filter(Assignment.course_id.in_(course_ids))
        )

    # ======================================================
    # Materials
    # ======================================================
    if CourseMaterial is not None:
        data["total_materials"] = _safe_count(
            db.query(func.count(CourseMaterial.id))
            .filter(CourseMaterial.course_id.in_(course_ids))
        )

    # ======================================================
    # Reviews
    # ======================================================
    if CourseReview is not None:
        avg_rating = (
            db.query(func.avg(CourseReview.overall_rating))
            .filter(CourseReview.course_id.in_(course_ids))
            .scalar()
        ) or 0

        total_reviews = _safe_count(
            db.query(func.count(CourseReview.id))
            .filter(CourseReview.course_id.in_(course_ids))
        )

        rating_distribution = [
            _safe_count(
                db.query(func.count(CourseReview.id)).filter(
                    CourseReview.course_id.in_(course_ids),
                    CourseReview.overall_rating >= i,
                    CourseReview.overall_rating < i + 1,
                )
            )
            for i in range(1, 6)
        ]

        data["avg_rating"] = round(float(avg_rating), 2)
        data["total_reviews"] = total_reviews
        data["rating_distribution"] = rating_distribution

    # ======================================================
    # Classes / Students
    # ======================================================
    if Class is not None:
        teacher_classes = db.query(Class).filter(Class.homeroom_teacher_id == teacher_id)
        classes = teacher_classes.all()
        data["total_classes"] = len(classes)

        if ClassEnrollment is not None and classes:
            class_ids = [c.id for c in classes]
            data["total_students"] = _safe_count(
                db.query(func.count(distinct(ClassEnrollment.student_id)))
                .filter(
                    ClassEnrollment.class_id.in_(class_ids),
                    ClassEnrollment.enrollment_status.in_(ACTIVE_ENROLL_STATUSES),
                )
            )
        else:
            # fallback nếu có current_students
            data["total_students"] = sum(int(getattr(c, "current_students", 0) or 0) for c in classes)

    return data