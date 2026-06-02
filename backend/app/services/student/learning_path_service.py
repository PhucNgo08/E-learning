from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.services.common.course_access_service import has_course_access

ACTIVE_PROGRESS_STATUSES = {"completed", "done", "finished"}
SUBMITTED_ASSIGNMENT_STATUSES = {"submitted", "graded", "late", "returned"}
VALID_ATTEMPT_STATUSES = {"submitted", "graded", "completed"}


@dataclass
class Step:
    title: str
    description: str
    step_type: str = "lesson"
    severity: str = "primary"
    url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "type": self.step_type,
            "severity": self.severity,
            "url": self.url,
        }


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _normalize_score(score: Any) -> float | None:
    """Chuẩn hóa điểm về thang 10 để dashboard dễ đọc."""
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


def _lesson_sort_key(lesson: Lesson):
    module = getattr(lesson, "module", None)
    return (
        int(getattr(module, "module_number", 0) or 0),
        int(getattr(lesson, "lesson_number", 0) or 0),
        getattr(lesson, "title", ""),
    )


def _get_course_lessons(db: Session, course_id: str) -> list[Lesson]:
    return (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .options(joinedload(Lesson.module))
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number.asc(), Lesson.lesson_number.asc())
        .all()
    )


def _get_lesson_progress_map(db: Session, user_id: str, lesson_ids: list[str]) -> dict[str, LessonProgress]:
    if not lesson_ids:
        return {}
    rows = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id.in_(lesson_ids),
        )
        .all()
    )
    return {row.lesson_id: row for row in rows}


def _get_quiz_summary(db: Session, user_id: str, course_id: str) -> dict[str, Any]:
    quizzes = db.query(Quiz).filter(Quiz.course_id == course_id).all()
    quiz_ids = [q.id for q in quizzes]
    if not quiz_ids:
        return {
            "total_quizzes": 0,
            "attempted_quizzes": 0,
            "quiz_average": None,
            "weak_quizzes": [],
        }

    attempts = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.quiz))
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id.in_(quiz_ids),
        )
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    best_by_quiz: dict[str, QuizAttempt] = {}
    for attempt in attempts:
        status = (attempt.status or "").strip().lower()
        if status and status not in VALID_ATTEMPT_STATUSES:
            continue
        score = _normalize_score(attempt.score)
        if score is None:
            continue
        current = best_by_quiz.get(attempt.quiz_id)
        if current is None or (score > (_normalize_score(current.score) or 0)):
            best_by_quiz[attempt.quiz_id] = attempt

    scores = [_normalize_score(a.score) for a in best_by_quiz.values()]
    scores = [s for s in scores if s is not None]
    avg = round(sum(scores) / len(scores), 2) if scores else None

    weak_quizzes = []
    for attempt in best_by_quiz.values():
        score = _normalize_score(attempt.score)
        if score is not None and score < 5:
            quiz = getattr(attempt, "quiz", None)
            weak_quizzes.append(
                {
                    "quiz_id": attempt.quiz_id,
                    "title": getattr(quiz, "title", "Quiz"),
                    "score": score,
                }
            )

    return {
        "total_quizzes": len(quizzes),
        "attempted_quizzes": len(best_by_quiz),
        "quiz_average": avg,
        "weak_quizzes": weak_quizzes[:5],
    }


def _get_assignment_summary(db: Session, user_id: str, course_id: str) -> dict[str, Any]:
    now = datetime.utcnow()
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .order_by(Assignment.due_date.asc())
        .all()
    )
    assignment_ids = [a.id for a in assignments]
    if not assignment_ids:
        return {
            "total_assignments": 0,
            "submitted_assignments": 0,
            "missing_assignments": [],
            "overdue_assignments": [],
        }

    submissions = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == user_id,
            AssignmentSubmission.assignment_id.in_(assignment_ids),
        )
        .all()
    )

    submitted_ids = {
        s.assignment_id
        for s in submissions
        if (s.status or "").strip().lower() in SUBMITTED_ASSIGNMENT_STATUSES
    }

    missing = []
    overdue = []
    for assignment in assignments:
        item = {
            "id": assignment.id,
            "title": assignment.title,
            "due_date": assignment.due_date,
            "url": f"/student/assignment/submit/{assignment.id}",
        }
        if assignment.id not in submitted_ids:
            missing.append(item)
            if assignment.due_date and assignment.due_date < now:
                overdue.append(item)

    return {
        "total_assignments": len(assignments),
        "submitted_assignments": len(submitted_ids),
        "missing_assignments": missing,
        "overdue_assignments": overdue,
    }


def get_learning_path(db: Session, user_id: str, course_id: str) -> dict[str, Any]:
    course = (
        db.query(Course)
        .options(joinedload(Course.teacher), joinedload(Course.modules))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        return {"status": "error", "message": "Không tìm thấy khóa học."}

    if not has_course_access(db, user_id, course_id):
        return {"status": "forbidden", "message": "Bạn chưa có quyền học khóa học này."}

    lessons = _get_course_lessons(db, course_id)
    lesson_ids = [lesson.id for lesson in lessons]
    progress_map = _get_lesson_progress_map(db, user_id, lesson_ids)

    completed_lessons = [lesson for lesson in lessons if _is_completed(progress_map.get(lesson.id))]
    incomplete_lessons = [lesson for lesson in lessons if lesson not in completed_lessons]
    total_lessons = len(lessons)
    progress_percent = round((len(completed_lessons) / total_lessons) * 100, 2) if total_lessons else 0.0

    quiz_summary = _get_quiz_summary(db, user_id, course_id)
    assignment_summary = _get_assignment_summary(db, user_id, course_id)

    recommended_steps: list[Step] = []

    overdue = assignment_summary["overdue_assignments"]
    if overdue:
        recommended_steps.append(
            Step(
                title="Ưu tiên xử lý bài tập quá hạn",
                description=f"Bạn đang có {len(overdue)} bài tập quá hạn/chưa nộp. Hãy nộp các bài này trước để không ảnh hưởng kết quả.",
                step_type="assignment",
                severity="danger",
                url=overdue[0].get("url"),
            )
        )

    if progress_percent < 40:
        next_lessons = sorted(incomplete_lessons, key=_lesson_sort_key)[:3]
        for lesson in next_lessons:
            module = getattr(lesson, "module", None)
            recommended_steps.append(
                Step(
                    title=f"Học tiếp: {lesson.title}",
                    description=f"Bài này thuộc module {getattr(module, 'module_number', '')}: {getattr(module, 'title', 'Chưa rõ module')}. Hoàn thành các bài nền tảng trước khi làm quiz.",
                    step_type="lesson",
                    severity="primary",
                    url=f"/student/lesson/view/{lesson.id}",
                )
            )
    elif progress_percent < 80 and incomplete_lessons:
        lesson = sorted(incomplete_lessons, key=_lesson_sort_key)[0]
        recommended_steps.append(
            Step(
                title=f"Tiếp tục bài học kế tiếp: {lesson.title}",
                description="Bạn đã có tiến độ tốt. Hãy duy trì nhịp học và hoàn thành bài tiếp theo.",
                step_type="lesson",
                severity="primary",
                url=f"/student/lesson/view/{lesson.id}",
            )
        )

    quiz_average = quiz_summary["quiz_average"]
    if quiz_average is None and quiz_summary["total_quizzes"]:
        recommended_steps.append(
            Step(
                title="Làm quiz sau khi hoàn thành bài học",
                description="Khóa học có quiz nhưng bạn chưa có kết quả. Hãy học xong bài trước rồi làm quiz để kiểm tra mức độ hiểu bài.",
                step_type="quiz",
                severity="warning",
                url=f"/student/quiz/course/{course_id}",
            )
        )
    elif quiz_average is not None and quiz_average < 5:
        recommended_steps.append(
            Step(
                title="Ôn lại kiến thức vì điểm quiz còn thấp",
                description=f"Điểm quiz trung bình hiện khoảng {quiz_average}/10. Bạn nên xem lại bài học và tài liệu trước khi làm tiếp.",
                step_type="quiz",
                severity="danger",
                url=f"/student/quiz/course/{course_id}",
            )
        )
    elif quiz_average is not None and quiz_average < 7:
        recommended_steps.append(
            Step(
                title="Củng cố thêm trước khi học phần mới",
                description=f"Điểm quiz trung bình hiện khoảng {quiz_average}/10. Hãy xem lại tài liệu để nâng kết quả lên mức tốt hơn.",
                step_type="material",
                severity="warning",
                url=f"/student/material/?course_id={course_id}",
            )
        )

    if progress_percent >= 80 and (quiz_average is None or quiz_average >= 7):
        recommended_steps.append(
            Step(
                title="Tổng ôn và hoàn thành khóa học",
                description="Bạn đang có tiến độ tốt. Hãy hoàn thành các bài còn lại, xem lại ghi chú và chuẩn bị bài kiểm tra cuối.",
                step_type="review",
                severity="success",
                url=f"/student/course/progress/{course_id}",
            )
        )

    if not recommended_steps:
        recommended_steps.append(
            Step(
                title="Tiếp tục duy trì tiến độ học",
                description="Không có cảnh báo lớn. Bạn nên tiếp tục học theo thứ tự bài học và làm đầy đủ quiz/bài tập.",
                step_type="general",
                severity="success",
                url=f"/student/course/progress/{course_id}",
            )
        )

    return {
        "status": "success",
        "course": course,
        "progress_percent": progress_percent,
        "completed_lessons": len(completed_lessons),
        "total_lessons": total_lessons,
        "incomplete_lessons": sorted(incomplete_lessons, key=_lesson_sort_key)[:8],
        "quiz_average": quiz_average,
        "quiz_summary": quiz_summary,
        "missing_assignments": assignment_summary["missing_assignments"],
        "overdue_assignments": assignment_summary["overdue_assignments"],
        "assignment_summary": assignment_summary,
        "recommended_steps": [step.as_dict() for step in recommended_steps[:8]],
    }
