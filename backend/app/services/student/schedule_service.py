from __future__ import annotations

from datetime import datetime, timedelta
import traceback

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.class_schedule import ClassSchedule
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.services.common.course_access_service import get_accessible_course_ids


DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

TYPE_LABELS = {
    "class_schedule": "Lịch học định kỳ",
    "lesson": "Bài học",
    "quiz": "Quiz",
    "exam": "Lịch thi / kiểm tra",
    "assignment_due": "Hạn nộp bài tập",
}


def _get_accessible_course_ids(db: Session, user_id: str) -> list[str]:
    """Lấy danh sách khóa học sinh viên có quyền học."""
    try:
        return [str(course_id) for course_id in get_accessible_course_ids(db, user_id) if course_id]
    except Exception as exc:
        print("❌ [_get_accessible_course_ids] Lỗi:", exc)
        traceback.print_exc()
        return []


def _start_of_week(value: datetime | None = None) -> datetime:
    today = value or datetime.now()
    return datetime(today.year, today.month, today.day) - timedelta(days=today.weekday())


def _safe_dt(value) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _format_dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%S") if value else None


def _date_display(value: datetime | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "-"


def _time_display(start_dt: datetime | None, end_dt: datetime | None = None) -> str:
    if not start_dt:
        return "-"
    if end_dt:
        return f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    return start_dt.strftime("%H:%M")


def _remaining_text(target: datetime | None, now: datetime | None = None) -> tuple[int | None, str]:
    """Trả về số ngày còn lại và chuỗi hiển thị cho deadline/lịch thi."""
    if not target:
        return None, "Chưa có thời gian"

    now = now or datetime.now()
    target_day = datetime(target.year, target.month, target.day)
    today = datetime(now.year, now.month, now.day)
    days_left = (target_day - today).days

    if days_left < 0:
        return days_left, f"Quá hạn {abs(days_left)} ngày"
    if days_left == 0:
        return 0, "Hôm nay"
    if days_left == 1:
        return 1, "Còn 1 ngày"
    return days_left, f"Còn {days_left} ngày"


def _event_type_from_lesson(lesson: Lesson) -> tuple[str, str]:
    title = (lesson.title or "").lower()
    content_type = (getattr(lesson, "content_type", "") or "").lower()

    if content_type == "quiz" or "quiz" in title or "trắc nghiệm" in title:
        return "quiz", "#f59e0b"

    if "thi" in title or "kiểm tra" in title or "exam" in title or "test" in title:
        return "exam", "#ef4444"

    return "lesson", "#16a34a"


def _event_type_from_quiz(quiz: Quiz) -> tuple[str, str]:
    title = (quiz.title or "").lower()
    quiz_type = (getattr(quiz, "quiz_type", "") or "").lower()

    if quiz_type == "graded" or "thi" in title or "kiểm tra" in title or "exam" in title or "test" in title:
        return "exam", "#dc2626"
    return "quiz", "#f59e0b"


def _deadline_color(days_left: int | None, is_done: bool = False) -> str:
    if is_done:
        return "#64748b"
    if days_left is None:
        return "#7c3aed"
    if days_left < 0:
        return "#991b1b"
    if days_left <= 3:
        return "#dc2626"
    if days_left <= 7:
        return "#f59e0b"
    return "#7c3aed"


def _course_from_quiz(quiz: Quiz):
    course = getattr(quiz, "course", None)
    if course:
        return course

    lesson = getattr(quiz, "lesson", None)
    module = getattr(lesson, "module", None) if lesson else None
    return getattr(module, "course", None) if module else None


def get_class_schedules(db: Session, user_id: str) -> list[dict]:
    """
    Lấy lịch học định kỳ của sinh viên:
    course_enrollments -> course_sections -> class_schedules.
    """
    try:
        course_ids = _get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        schedules = (
            db.query(ClassSchedule)
            .join(CourseSection, CourseSection.id == ClassSchedule.section_id)
            .join(Course, Course.id == CourseSection.course_id)
            .options(joinedload(ClassSchedule.section).joinedload(CourseSection.course))
            .filter(
                CourseSection.course_id.in_(course_ids),
                Course.status == "published",
            )
            .order_by(ClassSchedule.day_of_week.asc(), ClassSchedule.start_time.asc())
            .all()
        )

        start_week = _start_of_week()
        result: list[dict] = []

        for schedule in schedules:
            day_key = (schedule.day_of_week or "").lower()
            day_index = DAY_MAP.get(day_key)
            if day_index is None:
                continue

            date_of_class = start_week + timedelta(days=day_index)
            start_dt = datetime.combine(date_of_class.date(), schedule.start_time)
            end_dt = datetime.combine(date_of_class.date(), schedule.end_time)

            section = getattr(schedule, "section", None)
            course = getattr(section, "course", None)

            section_code = getattr(section, "section_code", "") or ""
            section_name = getattr(section, "section_name", "") or ""
            lesson_title = f"Lịch học định kỳ {section_code}".strip()
            if section_name:
                lesson_title = f"{lesson_title} - {section_name}"

            location = f"{schedule.building or ''} {schedule.room_number or ''}".strip()
            if not location:
                location = getattr(section, "location", None) or "Tại lớp"

            result.append(
                {
                    "id": f"class-{schedule.id}",
                    "course_name": course.course_name if course else "Khóa học",
                    "module_name": None,
                    "lesson_title": lesson_title,
                    "start": _format_dt(start_dt),
                    "end": _format_dt(end_dt),
                    "location": location,
                    "color": "#2563eb",
                    "type": "class_schedule",
                    "type_label": TYPE_LABELS["class_schedule"],
                    "date_display": _date_display(start_dt),
                    "time_display": _time_display(start_dt, end_dt),
                    "remaining_text": "",
                    "status_text": "",
                    "action_url": None,
                }
            )

        return result

    except Exception as exc:
        print("❌ [get_class_schedules] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_lesson_schedule(db: Session, user_id: str) -> list[dict]:
    """Lấy các bài học/quiz/bài kiểm tra có thời gian bắt đầu."""
    try:
        course_ids = _get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        lessons = (
            db.query(Lesson)
            .options(joinedload(Lesson.module).joinedload(Module.course))
            .join(Module, Lesson.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .filter(
                Course.id.in_(course_ids),
                Course.status == "published",
                Module.is_published == 1,
                Lesson.is_published == 1,
                Lesson.start_time.isnot(None),
            )
            .order_by(Lesson.start_time.asc())
            .all()
        )

        result: list[dict] = []

        for lesson in lessons:
            start_dt = _safe_dt(lesson.start_time)
            if not start_dt:
                continue

            end_dt = _safe_dt(lesson.end_time) or (start_dt + timedelta(minutes=lesson.duration_minutes or 90))
            type_key, color = _event_type_from_lesson(lesson)

            module = getattr(lesson, "module", None)
            course = getattr(module, "course", None)
            days_left, remaining = _remaining_text(start_dt)

            result.append(
                {
                    "id": f"lesson-{lesson.id}",
                    "lesson_id": str(lesson.id),
                    "course_name": course.course_name if course else "Khóa học",
                    "module_name": module.title if module else None,
                    "lesson_title": lesson.title or "Bài học",
                    "start": _format_dt(start_dt),
                    "end": _format_dt(end_dt),
                    "location": "Trực tuyến",
                    "color": color,
                    "type": type_key,
                    "type_label": TYPE_LABELS.get(type_key, "Sự kiện"),
                    "date_display": _date_display(start_dt),
                    "time_display": _time_display(start_dt, end_dt),
                    "days_left": days_left,
                    "remaining_text": remaining if type_key in ("quiz", "exam") else "",
                    "status_text": "",
                    "action_url": None,
                }
            )

        return result

    except Exception as exc:
        print("❌ [get_lesson_schedule] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_assignment_schedule(db: Session, user_id: str) -> list[dict]:
    """Hiện hạn nộp bài tập của các khóa sinh viên đang học."""
    try:
        course_ids = _get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        submitted_assignment_ids = {
            str(row[0])
            for row in (
                db.query(AssignmentSubmission.assignment_id)
                .filter(
                    AssignmentSubmission.student_id == user_id,
                    AssignmentSubmission.status.in_(("submitted", "graded", "late", "resubmitted")),
                )
                .all()
            )
            if row and row[0]
        }

        assignments = (
            db.query(Assignment)
            .options(joinedload(Assignment.course), joinedload(Assignment.module))
            .join(Course, Assignment.course_id == Course.id)
            .filter(
                Assignment.course_id.in_(course_ids),
                Course.status == "published",
                Assignment.due_date.isnot(None),
            )
            .order_by(Assignment.due_date.asc())
            .all()
        )

        result: list[dict] = []
        now = datetime.now()

        for assignment in assignments:
            due_dt = _safe_dt(assignment.due_date)
            if not due_dt:
                continue

            is_done = str(assignment.id) in submitted_assignment_ids
            days_left, remaining = _remaining_text(due_dt, now)
            color = _deadline_color(days_left, is_done=is_done)
            end_dt = due_dt + timedelta(minutes=30)

            result.append(
                {
                    "id": f"assignment-{assignment.id}",
                    "assignment_id": str(assignment.id),
                    "course_name": assignment.course.course_name if assignment.course else "Khóa học",
                    "module_name": assignment.module.title if assignment.module else None,
                    "lesson_title": f"Hạn nộp: {assignment.title}",
                    "start": _format_dt(due_dt),
                    "end": _format_dt(end_dt),
                    "location": "Nộp online",
                    "color": color,
                    "type": "assignment_due",
                    "type_label": TYPE_LABELS["assignment_due"],
                    "date_display": _date_display(due_dt),
                    "time_display": _time_display(due_dt),
                    "days_left": days_left,
                    "remaining_text": remaining,
                    "status_text": "Đã nộp" if is_done else "Chưa nộp",
                    "is_done": is_done,
                    "is_urgent": (not is_done) and (days_left is not None) and (0 <= days_left <= 7),
                    "action_url": f"/student/assignment/detail/{assignment.id}",
                }
            )

        return result

    except Exception as exc:
        print("❌ [get_assignment_schedule] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_quiz_schedule(db: Session, user_id: str) -> list[dict]:
    """Hiện lịch quiz/lịch thi dựa trên available_from/available_to của bảng quizzes."""
    try:
        course_ids = _get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        attempted_quiz_ids = {
            str(row[0])
            for row in (
                db.query(QuizAttempt.quiz_id)
                .filter(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.status.in_(("submitted", "graded")),
                )
                .all()
            )
            if row and row[0]
        }

        quizzes = (
            db.query(Quiz)
            .options(
                joinedload(Quiz.course),
                joinedload(Quiz.lesson).joinedload(Lesson.module).joinedload(Module.course),
            )
            .outerjoin(Lesson, Quiz.lesson_id == Lesson.id)
            .outerjoin(Module, Lesson.module_id == Module.id)
            .filter(
                Quiz.status == "published",
                Quiz.is_approved == True,  # noqa: E712 - SQLAlchemy boolean comparison
                or_(Quiz.course_id.in_(course_ids), Module.course_id.in_(course_ids)),
                or_(Quiz.available_from.isnot(None), Quiz.available_to.isnot(None)),
            )
            .order_by(Quiz.available_from.asc(), Quiz.available_to.asc())
            .all()
        )

        result: list[dict] = []
        now = datetime.now()

        for quiz in quizzes:
            start_dt = _safe_dt(quiz.available_from) or _safe_dt(quiz.available_to)
            if not start_dt:
                continue

            end_dt = _safe_dt(quiz.available_to)
            if not end_dt:
                end_dt = start_dt + timedelta(minutes=quiz.time_limit_minutes or 45)

            type_key, color = _event_type_from_quiz(quiz)
            course = _course_from_quiz(quiz)
            lesson = getattr(quiz, "lesson", None)
            module = getattr(lesson, "module", None) if lesson else None
            is_done = str(quiz.id) in attempted_quiz_ids
            days_left, remaining = _remaining_text(start_dt, now)

            if is_done:
                color = "#64748b"

            result.append(
                {
                    "id": f"quiz-{quiz.id}",
                    "quiz_id": str(quiz.id),
                    "course_name": course.course_name if course else "Khóa học",
                    "module_name": module.title if module else None,
                    "lesson_title": quiz.title or ("Bài kiểm tra" if type_key == "exam" else "Quiz"),
                    "start": _format_dt(start_dt),
                    "end": _format_dt(end_dt),
                    "location": "Làm trực tuyến",
                    "color": color,
                    "type": type_key,
                    "type_label": TYPE_LABELS.get(type_key, "Quiz"),
                    "date_display": _date_display(start_dt),
                    "time_display": _time_display(start_dt, end_dt),
                    "days_left": days_left,
                    "remaining_text": remaining,
                    "status_text": "Đã làm" if is_done else "Chưa làm",
                    "is_done": is_done,
                    "is_urgent": (not is_done) and (days_left is not None) and (0 <= days_left <= 7),
                    "action_url": f"/student/quiz/attempt/{quiz.id}",
                }
            )

        return result

    except Exception as exc:
        print("❌ [get_quiz_schedule] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_student_schedule(db: Session, user_id: str) -> list[dict]:
    """Gộp lịch học, lịch thi/quiz và hạn nộp bài tập."""
    try:
        all_events = (
            get_lesson_schedule(db, user_id)
            + get_class_schedules(db, user_id)
            + get_quiz_schedule(db, user_id)
            + get_assignment_schedule(db, user_id)
        )
        return sorted(all_events, key=lambda item: item.get("start") or "")
    except Exception as exc:
        print("❌ [get_student_schedule] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_upcoming_reminders(db: Session, user_id: str, days: int = 7) -> list[dict]:
    """Lấy các cảnh báo sắp tới: lịch thi/quiz và hạn nộp bài tập trong N ngày."""
    try:
        now = datetime.now()
        end = now + timedelta(days=days)
        reminders: list[dict] = []

        for event in get_student_schedule(db, user_id):
            if event.get("type") not in ("assignment_due", "quiz", "exam"):
                continue
            if event.get("is_done"):
                continue

            start_raw = event.get("start")
            if not start_raw:
                continue

            try:
                start_dt = datetime.fromisoformat(start_raw)
            except ValueError:
                continue

            if not (now <= start_dt <= end):
                continue

            event_copy = dict(event)
            if event_copy.get("type") == "assignment_due":
                event_copy["reminder_title"] = "Sắp đến hạn nộp bài tập"
                event_copy["reminder_message"] = f"{event_copy.get('course_name', 'Khóa học')} - {event_copy.get('lesson_title', '')}"
            elif event_copy.get("type") == "exam":
                event_copy["reminder_title"] = "Sắp tới lịch thi / kiểm tra"
                event_copy["reminder_message"] = f"{event_copy.get('course_name', 'Khóa học')} - {event_copy.get('lesson_title', '')}"
            else:
                event_copy["reminder_title"] = "Sắp tới lịch làm quiz"
                event_copy["reminder_message"] = f"{event_copy.get('course_name', 'Khóa học')} - {event_copy.get('lesson_title', '')}"

            reminders.append(event_copy)

        return sorted(reminders, key=lambda item: item.get("start") or "")
    except Exception as exc:
        print("❌ [get_upcoming_reminders] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_schedule_list(db: Session, user_id: str) -> list[dict]:
    return get_student_schedule(db, user_id)


def get_schedule_by_date(db: Session, user_id: str, date: datetime) -> list[dict]:
    target_date = date.strftime("%Y-%m-%d")
    return [event for event in get_student_schedule(db, user_id) if event.get("start", "").startswith(target_date)]


def get_schedule_for_week(db: Session, user_id: str, start_date: datetime) -> list[dict]:
    """Lấy lịch trong 7 ngày, dùng điều kiện < ngày kết thúc để tránh dư 1 ngày."""
    end_date = start_date + timedelta(days=7)
    start_key = start_date.strftime("%Y-%m-%d")
    end_key = end_date.strftime("%Y-%m-%d")

    return [
        event for event in get_student_schedule(db, user_id)
        if start_key <= event.get("start", "")[:10] < end_key
    ]
