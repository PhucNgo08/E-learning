"""Dashboard helpers cho Student - không sửa database."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.course_progress import CourseProgress
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")
DONE_QUIZ_STATUSES = ("submitted", "graded", "completed")


def _get_course_ids(db: Session, student_id: str) -> list[str]:
    rows = (
        db.query(CourseEnrollment.course_id)
        .filter(CourseEnrollment.user_id == student_id, CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .all()
    )
    return [str(r[0]) for r in rows if r and r[0]]


def get_continue_learning(db: Session, student_id: str) -> dict | None:
    course_ids = _get_course_ids(db, student_id)
    if not course_ids:
        return None

    progress = (
        db.query(LessonProgress, Lesson, Module, Course)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .join(Course, Course.id == Module.course_id)
        .filter(
            LessonProgress.user_id == student_id,
            Module.course_id.in_(course_ids),
            LessonProgress.progress_status.in_(["in_progress", "not_started"]),
        )
        .order_by(LessonProgress.updated_at.desc())
        .first()
    )

    if progress:
        lp, lesson, module, course = progress
    else:
        row = (
            db.query(Lesson, Module, Course)
            .join(Module, Module.id == Lesson.module_id)
            .join(Course, Course.id == Module.course_id)
            .filter(Module.course_id.in_(course_ids), Lesson.is_published == 1)
            .order_by(Course.created_at.desc(), Module.module_number.asc(), Lesson.lesson_number.asc())
            .first()
        )
        if not row:
            return None
        lesson, module, course = row
        lp = None

    total_lessons = (
        db.query(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id == course.id)
        .scalar()
        or 0
    )
    completed_lessons = (
        db.query(func.count(LessonProgress.id))
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .filter(LessonProgress.user_id == student_id, Module.course_id == course.id, LessonProgress.progress_status == "completed")
        .scalar()
        or 0
    )
    percent = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0

    course_progress = db.query(CourseProgress).filter(CourseProgress.user_id == student_id, CourseProgress.course_id == course.id).first()
    if course_progress and course_progress.progress_percent is not None:
        try:
            percent = float(course_progress.progress_percent)
        except Exception:
            pass

    return {
        "course": course,
        "module": module,
        "lesson": lesson,
        "lesson_progress": lp,
        "completed_lessons": completed_lessons,
        "total_lessons": total_lessons,
        "progress_percent": percent,
        "learn_url": f"/student/lesson/view/{lesson.id}",
    }


def get_dashboard_todo_summary(db: Session, student_id: str) -> dict:
    course_ids = _get_course_ids(db, student_id)
    if not course_ids:
        return {"assignments_missing": 0, "quizzes_pending": 0, "lessons_unfinished": 0}

    submitted_assignment_ids = db.query(AssignmentSubmission.assignment_id).filter(AssignmentSubmission.student_id == student_id).distinct()
    assignments_missing = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.course_id.in_(course_ids), ~Assignment.id.in_(submitted_assignment_ids))
        .scalar()
        or 0
    )

    done_quiz_ids = db.query(QuizAttempt.quiz_id).filter(QuizAttempt.user_id == student_id, QuizAttempt.status.in_(DONE_QUIZ_STATUSES)).distinct()
    quizzes_pending = (
        db.query(func.count(Quiz.id))
        .filter(Quiz.course_id.in_(course_ids), Quiz.status == "published", ~Quiz.id.in_(done_quiz_ids))
        .scalar()
        or 0
    )

    completed_lesson_ids = db.query(LessonProgress.lesson_id).filter(LessonProgress.user_id == student_id, LessonProgress.progress_status == "completed").distinct()
    lessons_unfinished = (
        db.query(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id.in_(course_ids), Lesson.is_published == 1, ~Lesson.id.in_(completed_lesson_ids))
        .scalar()
        or 0
    )

    return {
        "assignments_missing": int(assignments_missing),
        "quizzes_pending": int(quizzes_pending),
        "lessons_unfinished": int(lessons_unfinished),
    }
