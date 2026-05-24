"""Admin statistics service - tổng tiến độ học tập, không sửa database."""
from __future__ import annotations

from typing import Any

from sqlalchemy import distinct, func, true
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.rbac import Role
from app.models.user import User
from app.models.user_profile import UserProfile

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")
DONE_QUIZ_STATUSES = ("submitted", "graded", "completed")


def _count(query) -> int:
    try:
        return int(query.scalar() or 0)
    except Exception:
        return 0


def _course_not_deleted_condition():
    deleted_at_column = getattr(Course, "deleted_at", None)
    if deleted_at_column is not None:
        return deleted_at_column.is_(None)
    return true()


def _count_users_by_roles(db: Session, role_codes: list[str]) -> int:
    try:
        return _count(
            db.query(func.count(distinct(User.id)))
            .join(User.roles)
            .filter(Role.role_code.in_(role_codes))
        )
    except Exception:
        return 0


def _get_top_courses(db: Session, limit: int = 8) -> list[Any]:
    try:
        return (
            db.query(
                Course.id,
                Course.course_code,
                Course.course_name,
                func.count(CourseEnrollment.id).label("student_count"),
            )
            .outerjoin(
                CourseEnrollment,
                (CourseEnrollment.course_id == Course.id)
                & (
                    CourseEnrollment.enrollment_status.in_(
                        ACTIVE_ENROLLMENT_STATUSES
                    )
                ),
            )
            .filter(_course_not_deleted_condition())
            .group_by(Course.id, Course.course_code, Course.course_name)
            .order_by(func.count(CourseEnrollment.id).desc())
            .limit(limit)
            .all()
        )
    except Exception:
        return []


def _get_top_students(db: Session, limit: int = 8) -> list[Any]:
    try:
        return (
            db.query(
                User.id,
                User.username,
                User.email,
                UserProfile.full_name,
                func.count(LessonProgress.id).label("completed_count"),
            )
            .join(LessonProgress, LessonProgress.user_id == User.id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .filter(LessonProgress.progress_status == "completed")
            .group_by(User.id, User.username, User.email, UserProfile.full_name)
            .order_by(func.count(LessonProgress.id).desc())
            .limit(limit)
            .all()
        )
    except Exception:
        return []


def _get_inactive_students(db: Session, limit: int = 10) -> list[Any]:
    try:
        started_student_ids = db.query(LessonProgress.user_id).distinct()
        return (
            db.query(User, UserProfile)
            .join(User.roles)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .filter(
                Role.role_code == "student",
                ~User.id.in_(started_student_ids),
            )
            .limit(limit)
            .all()
        )
    except Exception:
        return []


def get_learning_progress_overview(db: Session) -> dict[str, Any]:
    total_students = _count_users_by_roles(db, ["student"])
    total_teachers = _count_users_by_roles(
        db,
        ["teacher", "teaching_assistant"],
    )

    total_courses = _count(
        db.query(func.count(Course.id)).filter(_course_not_deleted_condition())
    )
    published_courses = _count(
        db.query(func.count(Course.id)).filter(
            Course.status == "published",
            _course_not_deleted_condition(),
        )
    )

    total_enrollments = _count(
        db.query(func.count(CourseEnrollment.id)).filter(
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES)
        )
    )

    total_lessons = _count(db.query(func.count(Lesson.id)))
    completed_lessons = _count(
        db.query(func.count(LessonProgress.id)).filter(
            LessonProgress.progress_status == "completed"
        )
    )

    total_assignments = _count(db.query(func.count(Assignment.id)))
    total_submissions = _count(db.query(func.count(AssignmentSubmission.id)))
    graded_submissions = _count(
        db.query(func.count(AssignmentSubmission.id)).filter(
            AssignmentSubmission.status == "graded"
        )
    )

    total_quizzes = _count(db.query(func.count(Quiz.id)))
    quiz_attempts = _count(
        db.query(func.count(QuizAttempt.id)).filter(
            QuizAttempt.status.in_(DONE_QUIZ_STATUSES)
        )
    )

    lesson_completion_rate = (
        round((completed_lessons / total_lessons) * 100, 1)
        if total_lessons
        else 0
    )
    assignment_submit_rate = (
        round((total_submissions / total_assignments) * 100, 1)
        if total_assignments
        else 0
    )

    return {
        "summary": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_courses": total_courses,
            "published_courses": published_courses,
            "total_enrollments": total_enrollments,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "lesson_completion_rate": lesson_completion_rate,
            "total_assignments": total_assignments,
            "total_submissions": total_submissions,
            "graded_submissions": graded_submissions,
            "assignment_submit_rate": assignment_submit_rate,
            "total_quizzes": total_quizzes,
            "quiz_attempts": quiz_attempts,
        },
        "top_courses": _get_top_courses(db),
        "top_students": _get_top_students(db),
        "inactive_students": _get_inactive_students(db),
    }
