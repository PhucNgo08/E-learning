"""
Teacher statistics service - nâng cấp an toàn, không sửa database.
Dùng lại các bảng hiện có: courses, course_enrollments, modules, lessons,
lesson_progress, assignments, assignment_submissions, quizzes, quiz_attempts.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy import func, distinct
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
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.student_profile import StudentProfile

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")
DONE_QUIZ_STATUSES = ("submitted", "graded", "completed")


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _percent(done: int, total: int) -> float:
    if not total:
        return 0.0
    return round(min(100.0, max(0.0, (done / total) * 100)), 1)


def _student_name(user: User | None, profile: UserProfile | None = None) -> str:
    if profile and getattr(profile, "full_name", None):
        return profile.full_name
    if user and getattr(user, "profile", None) and getattr(user.profile, "full_name", None):
        return user.profile.full_name
    if user and getattr(user, "username", None):
        return user.username
    if user and getattr(user, "email", None):
        return user.email
    return "Không rõ"


def get_teacher_statistics(db: Session, teacher_id: str) -> dict:
    """Giữ tương thích với trang /teacher/statistics/index cũ."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    tomorrow_start = today_start + timedelta(days=1)

    courses = (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.created_at.desc())
        .all()
    )
    course_ids = [c.id for c in courses]

    data = {
        "total_courses": len(courses),
        "published_courses": sum(1 for c in courses if getattr(c, "status", "") == "published"),
        "draft_courses": sum(1 for c in courses if getattr(c, "status", "") == "draft"),
        "archived_courses": sum(1 for c in courses if getattr(c, "status", "") == "archived"),
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
        "rating_distribution": [0, 0, 0, 0, 0],
        "total_classes": 0,
        "total_students": 0,
        "latest_courses": [
            {
                "id": c.id,
                "course_name": c.course_name,
                "status": c.status,
                "created_at": c.created_at,
            }
            for c in courses[:5]
        ],
    }

    if not course_ids:
        return data

    modules = db.query(Module).filter(Module.course_id.in_(course_ids)).all()
    data["total_modules"] = len(modules)
    data["published_modules"] = sum(1 for m in modules if bool(getattr(m, "is_published", False)))

    lessons = (
        db.query(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id.in_(course_ids))
        .all()
    )
    data["total_lessons"] = len(lessons)
    data["published_lessons"] = sum(1 for l in lessons if bool(getattr(l, "is_published", False)))
    data["today_lessons"] = (
        db.query(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id.in_(course_ids), Lesson.start_time >= today_start, Lesson.start_time < tomorrow_start)
        .scalar()
        or 0
    )
    data["upcoming_lessons"] = (
        db.query(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id.in_(course_ids), Lesson.start_time >= now)
        .scalar()
        or 0
    )

    quizzes = db.query(Quiz).filter(Quiz.course_id.in_(course_ids)).all()
    data["total_quizzes"] = len(quizzes)
    data["graded_quizzes"] = sum(1 for q in quizzes if getattr(q, "quiz_type", "") == "graded")
    data["practice_quizzes"] = data["total_quizzes"] - data["graded_quizzes"]

    data["total_assignments"] = db.query(func.count(Assignment.id)).filter(Assignment.course_id.in_(course_ids)).scalar() or 0
    data["total_students"] = (
        db.query(func.count(distinct(CourseEnrollment.user_id)))
        .filter(CourseEnrollment.course_id.in_(course_ids), CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .scalar()
        or 0
    )

    return data


def get_teacher_courses(db: Session, teacher_id: str) -> list[Course]:
    return (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.created_at.desc(), Course.course_name.asc())
        .all()
    )


def get_course_student_progress(db: Session, teacher_id: str, course_id: str | None = None) -> dict:
    courses = get_teacher_courses(db, teacher_id)
    if not courses:
        return {"courses": [], "selected_course": None, "rows": [], "summary": {}}

    course_ids = [c.id for c in courses]
    selected_course = None
    if course_id and course_id in course_ids:
        selected_course = next((c for c in courses if c.id == course_id), None)
    if not selected_course:
        selected_course = courses[0]

    cid = selected_course.id

    total_lessons = (
        db.query(func.count(Lesson.id))
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id == cid)
        .scalar()
        or 0
    )
    total_assignments = db.query(func.count(Assignment.id)).filter(Assignment.course_id == cid).scalar() or 0
    total_quizzes = db.query(func.count(Quiz.id)).filter(Quiz.course_id == cid).scalar() or 0

    enrolled = (
        db.query(User, UserProfile, StudentProfile)
        .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .filter(
            CourseEnrollment.course_id == cid,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .order_by(UserProfile.full_name.asc(), User.username.asc())
        .all()
    )

    rows = []
    for user, profile, student_profile in enrolled:
        completed_lessons = (
            db.query(func.count(LessonProgress.id))
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .filter(
                LessonProgress.user_id == user.id,
                Module.course_id == cid,
                LessonProgress.progress_status == "completed",
            )
            .scalar()
            or 0
        )
        submitted_assignments = (
            db.query(func.count(distinct(AssignmentSubmission.assignment_id)))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(Assignment.course_id == cid, AssignmentSubmission.student_id == user.id)
            .scalar()
            or 0
        )
        graded_assignments = (
            db.query(func.count(AssignmentSubmission.id))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(Assignment.course_id == cid, AssignmentSubmission.student_id == user.id, AssignmentSubmission.status == "graded")
            .scalar()
            or 0
        )
        avg_assignment_grade = (
            db.query(func.avg(AssignmentSubmission.grade))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(Assignment.course_id == cid, AssignmentSubmission.student_id == user.id, AssignmentSubmission.grade.isnot(None))
            .scalar()
        )
        done_quizzes = (
            db.query(func.count(distinct(QuizAttempt.quiz_id)))
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .filter(Quiz.course_id == cid, QuizAttempt.user_id == user.id, QuizAttempt.status.in_(DONE_QUIZ_STATUSES))
            .scalar()
            or 0
        )
        avg_quiz_score = (
            db.query(func.avg(QuizAttempt.score))
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .filter(Quiz.course_id == cid, QuizAttempt.user_id == user.id, QuizAttempt.status.in_(DONE_QUIZ_STATUSES), QuizAttempt.score.isnot(None))
            .scalar()
        )

        lesson_percent = _percent(completed_lessons, total_lessons)
        assignment_percent = _percent(submitted_assignments, total_assignments)
        quiz_percent = _percent(done_quizzes, total_quizzes)
        overall = round(lesson_percent * 0.5 + assignment_percent * 0.3 + quiz_percent * 0.2, 1)

        if overall >= 80:
            status_text = "Tốt"
            status_class = "success"
        elif overall >= 40:
            status_text = "Đang học"
            status_class = "primary"
        elif overall > 0:
            status_text = "Cần theo dõi"
            status_class = "warning"
        else:
            status_text = "Chưa bắt đầu"
            status_class = "secondary"

        rows.append({
            "student": user,
            "full_name": _student_name(user, profile),
            "email": user.email,
            "mssv": getattr(student_profile, "mssv", None),
            "completed_lessons": _safe_int(completed_lessons),
            "total_lessons": _safe_int(total_lessons),
            "lesson_percent": lesson_percent,
            "submitted_assignments": _safe_int(submitted_assignments),
            "graded_assignments": _safe_int(graded_assignments),
            "total_assignments": _safe_int(total_assignments),
            "assignment_percent": assignment_percent,
            "avg_assignment_grade": round(_safe_float(avg_assignment_grade), 2),
            "done_quizzes": _safe_int(done_quizzes),
            "total_quizzes": _safe_int(total_quizzes),
            "quiz_percent": quiz_percent,
            "avg_quiz_score": round(_safe_float(avg_quiz_score), 2),
            "overall_progress": overall,
            "status_text": status_text,
            "status_class": status_class,
        })

    summary = {
        "total_students": len(rows),
        "avg_progress": round(sum(r["overall_progress"] for r in rows) / len(rows), 1) if rows else 0,
        "need_attention": sum(1 for r in rows if r["overall_progress"] < 40),
        "completed_good": sum(1 for r in rows if r["overall_progress"] >= 80),
        "total_lessons": _safe_int(total_lessons),
        "total_assignments": _safe_int(total_assignments),
        "total_quizzes": _safe_int(total_quizzes),
    }

    return {"courses": courses, "selected_course": selected_course, "rows": rows, "summary": summary}


def get_student_progress_detail(db: Session, teacher_id: str, course_id: str, student_id: str) -> dict | None:
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher_id).first()
    if not course:
        return None

    enrollment = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.course_id == course_id, CourseEnrollment.user_id == student_id, CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES))
        .first()
    )
    if not enrollment:
        return None

    student = db.query(User).filter(User.id == student_id).first()
    profile = db.query(UserProfile).filter(UserProfile.user_id == student_id).first()
    student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == student_id).first()

    modules = db.query(Module).filter(Module.course_id == course_id).order_by(Module.module_number.asc()).all()
    module_rows = []
    for module in modules:
        lessons = db.query(Lesson).filter(Lesson.module_id == module.id).order_by(Lesson.lesson_number.asc()).all()
        lesson_rows = []
        for lesson in lessons:
            progress = db.query(LessonProgress).filter(LessonProgress.user_id == student_id, LessonProgress.lesson_id == lesson.id).first()
            lesson_rows.append({"lesson": lesson, "progress": progress, "completed": bool(progress and progress.progress_status == "completed")})
        module_rows.append({"module": module, "lessons": lesson_rows})

    assignment_rows = []
    assignments = db.query(Assignment).filter(Assignment.course_id == course_id).order_by(Assignment.due_date.asc()).all()
    for assignment in assignments:
        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == assignment.id, AssignmentSubmission.student_id == student_id)
            .order_by(AssignmentSubmission.submission_time.desc())
            .first()
        )
        assignment_rows.append({"assignment": assignment, "submission": submission})

    quiz_rows = []
    quizzes = db.query(Quiz).filter(Quiz.course_id == course_id).order_by(Quiz.created_at.desc()).all()
    for quiz in quizzes:
        attempt = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == student_id)
            .order_by(QuizAttempt.attempt_number.desc(), QuizAttempt.started_at.desc())
            .first()
        )
        quiz_rows.append({"quiz": quiz, "attempt": attempt})

    overall_data = get_course_student_progress(db, teacher_id, course_id)
    student_summary = next((r for r in overall_data.get("rows", []) if str(r["student"].id) == str(student_id)), None)

    return {
        "course": course,
        "student": student,
        "profile": profile,
        "student_profile": student_profile,
        "full_name": _student_name(student, profile),
        "summary": student_summary,
        "modules": module_rows,
        "assignments": assignment_rows,
        "quizzes": quiz_rows,
    }
