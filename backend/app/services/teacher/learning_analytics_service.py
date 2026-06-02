from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.models.user_profile import UserProfile

ACTIVE_ENROLLMENT_STATUSES = {"approved", "active", "completed"}
ACTIVE_PROGRESS_STATUSES = {"completed", "done", "finished"}
SUBMITTED_ASSIGNMENT_STATUSES = {"submitted", "graded", "late", "returned"}
VALID_ATTEMPT_STATUSES = {"submitted", "graded", "completed"}


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _normalize_score(score: Any) -> float | None:
    if score is None:
        return None
    value = _to_float(score)
    if value > 10:
        value = value / 10
    return round(max(0.0, min(value, 10.0)), 2)


def _is_completed(progress: LessonProgress | None) -> bool:
    if not progress:
        return False
    status = (progress.progress_status or "").strip().lower()
    return (
        status in ACTIVE_PROGRESS_STATUSES
        or int(progress.completion_percentage or 0) >= 100
        or progress.completed_at is not None
    )


def _student_display_name(user: User) -> str:
    profile = getattr(user, "profile", None)
    full_name = getattr(profile, "full_name", None)
    return full_name or getattr(user, "username", "Học viên")


def get_teacher_courses_overview(db: Session, teacher_id: str) -> dict[str, Any]:
    courses = (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.created_at.desc())
        .all()
    )

    course_cards = []
    for course in courses:
        summary = get_course_learning_analytics(db, teacher_id, course.id, compact=True)
        if summary.get("status") == "success":
            course_cards.append(summary)

    total_students = sum(item.get("total_students", 0) for item in course_cards)
    avg_progress = round(
        sum(item.get("avg_progress", 0) for item in course_cards) / len(course_cards), 2
    ) if course_cards else 0.0
    avg_quiz_values = [item.get("avg_quiz") for item in course_cards if item.get("avg_quiz") is not None]
    avg_quiz = round(sum(avg_quiz_values) / len(avg_quiz_values), 2) if avg_quiz_values else None

    return {
        "courses": course_cards,
        "total_courses": len(courses),
        "total_students": total_students,
        "avg_progress": avg_progress,
        "avg_quiz": avg_quiz,
        "at_risk_total": sum(item.get("at_risk_count", 0) for item in course_cards),
    }


def _get_active_students(db: Session, course_id: str) -> list[User]:
    enrollments = (
        db.query(CourseEnrollment)
        .options(joinedload(CourseEnrollment.user).joinedload(User.profile))
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .all()
    )
    return [e.user for e in enrollments if e.user]


def _get_course_lessons(db: Session, course_id: str) -> list[Lesson]:
    return (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .options(joinedload(Lesson.module))
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number.asc(), Lesson.lesson_number.asc())
        .all()
    )


def _get_student_progress(db: Session, student_id: str, lessons: list[Lesson]) -> tuple[float, int]:
    lesson_ids = [lesson.id for lesson in lessons]
    if not lesson_ids:
        return 0.0, 0

    rows = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == student_id,
            LessonProgress.lesson_id.in_(lesson_ids),
        )
        .all()
    )
    progress_map = {row.lesson_id: row for row in rows}
    completed = sum(1 for lesson in lessons if _is_completed(progress_map.get(lesson.id)))
    percent = round((completed / len(lessons)) * 100, 2) if lessons else 0.0
    return percent, completed


def _get_student_quiz_average(db: Session, student_id: str, quiz_ids: list[str]) -> float | None:
    if not quiz_ids:
        return None
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == student_id,
            QuizAttempt.quiz_id.in_(quiz_ids),
        )
        .all()
    )
    best_by_quiz: dict[str, float] = {}
    for attempt in attempts:
        status = (attempt.status or "").strip().lower()
        if status and status not in VALID_ATTEMPT_STATUSES:
            continue
        score = _normalize_score(attempt.score)
        if score is None:
            continue
        best_by_quiz[attempt.quiz_id] = max(score, best_by_quiz.get(attempt.quiz_id, 0.0))
    if not best_by_quiz:
        return None
    return round(sum(best_by_quiz.values()) / len(best_by_quiz), 2)


def _get_assignment_counts(db: Session, student_id: str, assignments: list[Assignment]) -> dict[str, int]:
    now = datetime.utcnow()
    assignment_ids = [assignment.id for assignment in assignments]
    if not assignment_ids:
        return {"submitted": 0, "missing": 0, "overdue": 0}

    submissions = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.assignment_id.in_(assignment_ids),
        )
        .all()
    )
    submitted_ids = {
        submission.assignment_id
        for submission in submissions
        if (submission.status or "").strip().lower() in SUBMITTED_ASSIGNMENT_STATUSES
    }
    missing = 0
    overdue = 0
    for assignment in assignments:
        if assignment.id not in submitted_ids:
            missing += 1
            if assignment.due_date and assignment.due_date < now:
                overdue += 1
    return {"submitted": len(submitted_ids), "missing": missing, "overdue": overdue}


def get_course_learning_analytics(
    db: Session,
    teacher_id: str,
    course_id: str,
    compact: bool = False,
) -> dict[str, Any]:
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher_id).first()
    if not course:
        return {"status": "forbidden", "message": "Không tìm thấy khóa học hoặc bạn không phụ trách khóa này."}

    students = _get_active_students(db, course_id)
    lessons = _get_course_lessons(db, course_id)
    quizzes = db.query(Quiz).filter(Quiz.course_id == course_id).all()
    quiz_ids = [quiz.id for quiz in quizzes]
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).all()

    student_rows = []
    progress_values = []
    quiz_values = []
    assignment_submitted_total = 0
    assignment_missing_total = 0
    assignment_overdue_total = 0

    for student in students:
        progress_percent, completed_lessons = _get_student_progress(db, student.id, lessons)
        quiz_average = _get_student_quiz_average(db, student.id, quiz_ids)
        assignment_counts = _get_assignment_counts(db, student.id, assignments)

        progress_values.append(progress_percent)
        if quiz_average is not None:
            quiz_values.append(quiz_average)
        assignment_submitted_total += assignment_counts["submitted"]
        assignment_missing_total += assignment_counts["missing"]
        assignment_overdue_total += assignment_counts["overdue"]

        reasons = []
        if progress_percent < 40:
            reasons.append("Tiến độ thấp")
        if quiz_average is not None and quiz_average < 5:
            reasons.append("Điểm quiz thấp")
        if assignment_counts["overdue"] > 0:
            reasons.append("Có bài tập quá hạn")
        if lessons and completed_lessons == 0:
            reasons.append("Chưa hoàn thành bài học nào")

        profile = getattr(student, "profile", None)
        student_profile = getattr(student, "student_profile", None)
        student_rows.append(
            {
                "id": student.id,
                "username": student.username,
                "email": student.email,
                "full_name": _student_display_name(student),
                "mssv": getattr(student_profile, "mssv", "") if student_profile else "",
                "progress_percent": progress_percent,
                "completed_lessons": completed_lessons,
                "total_lessons": len(lessons),
                "quiz_average": quiz_average,
                "submitted_assignments": assignment_counts["submitted"],
                "missing_assignments": assignment_counts["missing"],
                "overdue_assignments": assignment_counts["overdue"],
                "need_support": bool(reasons),
                "risk_reasons": reasons,
            }
        )

    at_risk_students = [row for row in student_rows if row["need_support"]]
    avg_progress = round(sum(progress_values) / len(progress_values), 2) if progress_values else 0.0
    avg_quiz = round(sum(quiz_values) / len(quiz_values), 2) if quiz_values else None

    completed_students = sum(1 for value in progress_values if value >= 100)
    unfinished_students = max(0, len(students) - completed_students)

    weak_lessons = []
    if students and lessons:
        for lesson in lessons:
            completed_count = (
                db.query(func.count(LessonProgress.id))
                .filter(
                    LessonProgress.lesson_id == lesson.id,
                    LessonProgress.user_id.in_([s.id for s in students]),
                    (
                        (LessonProgress.progress_status.in_(ACTIVE_PROGRESS_STATUSES))
                        | (LessonProgress.completion_percentage >= 100)
                        | (LessonProgress.completed_at.isnot(None))
                    ),
                )
                .scalar()
                or 0
            )
            incomplete_count = len(students) - int(completed_count)
            if incomplete_count > 0:
                module = getattr(lesson, "module", None)
                weak_lessons.append(
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "module_title": getattr(module, "title", ""),
                        "module_number": getattr(module, "module_number", ""),
                        "incomplete_count": incomplete_count,
                        "incomplete_percent": round((incomplete_count / len(students)) * 100, 2),
                    }
                )
    weak_lessons = sorted(weak_lessons, key=lambda item: item["incomplete_count"], reverse=True)[:8]

    result = {
        "status": "success",
        "course": course,
        "total_students": len(students),
        "total_lessons": len(lessons),
        "total_quizzes": len(quizzes),
        "total_assignments": len(assignments),
        "avg_progress": avg_progress,
        "avg_quiz": avg_quiz,
        "completed_students": completed_students,
        "unfinished_students": unfinished_students,
        "assignment_submitted_total": assignment_submitted_total,
        "assignment_missing_total": assignment_missing_total,
        "assignment_overdue_total": assignment_overdue_total,
        "at_risk_students": at_risk_students,
        "at_risk_count": len(at_risk_students),
        "weak_lessons": weak_lessons,
    }

    if not compact:
        result["student_rows"] = sorted(
            student_rows,
            key=lambda row: (not row["need_support"], row["progress_percent"], row["full_name"]),
        )

    return result
