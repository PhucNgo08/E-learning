"""Student todo service - không sửa database."""
from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.notification import Notification

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")
DONE_QUIZ_STATUSES = ("submitted", "graded", "completed")


def get_student_course_ids(db: Session, student_id: str) -> list[str]:
    rows = (
        db.query(CourseEnrollment.course_id)
        .filter(
            CourseEnrollment.user_id == student_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .all()
    )
    return [str(r[0]) for r in rows if r and r[0]]


def get_student_todo(db: Session, student_id: str) -> dict:
    now = datetime.utcnow()
    soon = now + timedelta(days=7)
    course_ids = get_student_course_ids(db, student_id)

    result = {
        "course_ids": course_ids,
        "due_assignments": [],
        "missing_assignments": [],
        "pending_quizzes": [],
        "unfinished_lessons": [],
        "graded_submissions": [],
        "notifications": [],
        "summary": {
            "due_assignments": 0,
            "missing_assignments": 0,
            "pending_quizzes": 0,
            "unfinished_lessons": 0,
            "unread_notifications": 0,
        },
    }
    if not course_ids:
        return result

    submitted_assignment_ids = {
        str(row[0])
        for row in db.query(AssignmentSubmission.assignment_id)
        .filter(AssignmentSubmission.student_id == student_id)
        .distinct()
        .all()
        if row and row[0]
    }

    assignment_query = (
        db.query(Assignment, Course)
        .join(Course, Course.id == Assignment.course_id)
        .filter(Assignment.course_id.in_(course_ids))
        .order_by(Assignment.due_date.asc())
    )
    for assignment, course in assignment_query.all():
        if str(assignment.id) in submitted_assignment_ids:
            continue
        item = {"assignment": assignment, "course": course}
        if assignment.due_date and now <= assignment.due_date <= soon:
            result["due_assignments"].append(item)
        if not assignment.due_date or assignment.due_date >= now:
            result["missing_assignments"].append(item)

    done_quiz_ids = {
        str(row[0])
        for row in db.query(QuizAttempt.quiz_id)
        .filter(QuizAttempt.user_id == student_id, QuizAttempt.status.in_(DONE_QUIZ_STATUSES))
        .distinct()
        .all()
        if row and row[0]
    }
    quizzes = (
        db.query(Quiz, Course)
        .join(Course, Course.id == Quiz.course_id)
        .filter(Quiz.course_id.in_(course_ids), Quiz.status == "published")
        .order_by(
        case((Quiz.available_to.is_(None), 1), else_=0),
        Quiz.available_to.asc(),
        Quiz.created_at.desc(),
    )
        .all()
    )
    for quiz, course in quizzes:
        if str(quiz.id) not in done_quiz_ids:
            result["pending_quizzes"].append({"quiz": quiz, "course": course})

    completed_lesson_ids = {
        str(row[0])
        for row in db.query(LessonProgress.lesson_id)
        .filter(LessonProgress.user_id == student_id, LessonProgress.progress_status == "completed")
        .all()
        if row and row[0]
    }
    lessons = (
        db.query(Lesson, Module, Course)
        .join(Module, Module.id == Lesson.module_id)
        .join(Course, Course.id == Module.course_id)
        .filter(Module.course_id.in_(course_ids), Lesson.is_published == 1)
        .order_by(Course.course_name.asc(), Module.module_number.asc(), Lesson.lesson_number.asc())
        .limit(20)
        .all()
    )
    for lesson, module, course in lessons:
        if str(lesson.id) not in completed_lesson_ids:
            result["unfinished_lessons"].append({"lesson": lesson, "module": module, "course": course})

    result["graded_submissions"] = (
        db.query(AssignmentSubmission, Assignment, Course)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .join(Course, Course.id == Assignment.course_id)
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "graded",
            Assignment.course_id.in_(course_ids),
        )
        .order_by(
        case((AssignmentSubmission.graded_at.is_(None), 1), else_=0),
        AssignmentSubmission.graded_at.desc(),
        AssignmentSubmission.updated_at.desc(),
        )
        .limit(10)
        .all()
    )

    result["notifications"] = (
        db.query(Notification)
        .filter(Notification.user_id == student_id, Notification.is_read == 0)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )

    result["summary"] = {
        "due_assignments": len(result["due_assignments"]),
        "missing_assignments": len(result["missing_assignments"]),
        "pending_quizzes": len(result["pending_quizzes"]),
        "unfinished_lessons": len(result["unfinished_lessons"]),
        "unread_notifications": len(result["notifications"]),
    }
    return result
