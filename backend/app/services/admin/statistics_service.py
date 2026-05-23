"""Admin statistics service - tổng tiến độ học tập, không sửa database."""
from __future__ import annotations

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.rbac import Role
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")
DONE_QUIZ_STATUSES = ("submitted", "graded", "completed")


def _count(query) -> int:
    try:
        return int(query.scalar() or 0)
    except Exception:
        return 0


def get_learning_progress_overview(db: Session) -> dict:
    total_students = _count(
        db.query(func.count(distinct(User.id))).join(User.roles).filter(Role.role_code == "student")
    )
    total_teachers = _count(
        db.query(func.count(distinct(User.id))).join(User.roles).filter(Role.role_code.in_(["teacher", "teaching_assistant"]))
    )
    total_courses = _count(db.query(func.count(Course.id)).filter(Course.deleted_at.is_(None) if hasattr(Course, "deleted_at") else True))
    published_courses = _count(db.query(func.count(Course.id)).filter(Course.status == "published"))
    total_enrollments = _count(db.query(func.count(CourseEnrollment.id)).filter(CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES)))
    total_lessons = _count(db.query(func.count(Lesson.id)))
    completed_lessons = _count(db.query(func.count(LessonProgress.id)).filter(LessonProgress.progress_status == "completed"))
    total_assignments = _count(db.query(func.count(Assignment.id)))
    total_submissions = _count(db.query(func.count(AssignmentSubmission.id)))
    graded_submissions = _count(db.query(func.count(AssignmentSubmission.id)).filter(AssignmentSubmission.status == "graded"))
    total_quizzes = _count(db.query(func.count(Quiz.id)))
    quiz_attempts = _count(db.query(func.count(QuizAttempt.id)).filter(QuizAttempt.status.in_(DONE_QUIZ_STATUSES)))

    lesson_completion_rate = round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0
    assignment_submit_rate = round((total_submissions / total_assignments) * 100, 1) if total_assignments else 0

    top_courses = (
        db.query(
            Course.id,
            Course.course_code,
            Course.course_name,
            func.count(CourseEnrollment.id).label("student_count"),
        )
        .outerjoin(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        .filter((CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES)) | (CourseEnrollment.id.is_(None)))
        .group_by(Course.id, Course.course_code, Course.course_name)
        .order_by(func.count(CourseEnrollment.id).desc())
        .limit(8)
        .all()
    )

    top_students = (
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
        .limit(8)
        .all()
    )

    started_student_ids = db.query(LessonProgress.user_id).distinct()
    inactive_students = (
        db.query(User, UserProfile)
        .join(User.roles)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(Role.role_code == "student", ~User.id.in_(started_student_ids))
        .limit(10)
        .all()
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
        "top_courses": top_courses,
        "top_students": top_students,
        "inactive_students": inactive_students,
    }
