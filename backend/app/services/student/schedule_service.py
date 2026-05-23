from __future__ import annotations

from datetime import datetime, timedelta
import traceback

from sqlalchemy.orm import Session, joinedload

from app.models.class_schedule import ClassSchedule
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.lesson import Lesson
from app.models.module import Module
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
    "exam": "Bài kiểm tra",
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


def _event_type_from_lesson(lesson: Lesson) -> tuple[str, str]:
    title = (lesson.title or "").lower()
    content_type = (getattr(lesson, "content_type", "") or "").lower()

    if content_type == "quiz" or "quiz" in title or "trắc nghiệm" in title:
        return "quiz", "#f59e0b"

    if "thi" in title or "kiểm tra" in title or "exam" in title or "test" in title:
        return "exam", "#ef4444"

    return "lesson", "#16a34a"


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
                    "course_name": course.course_name if course else "Khóa học",
                    "module_name": None,
                    "lesson_title": lesson_title,
                    "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "location": location,
                    "color": "#2563eb",
                    "type": "class_schedule",
                    "type_label": TYPE_LABELS["class_schedule"],
                    "date_display": start_dt.strftime("%d/%m/%Y"),
                    "time_display": f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}",
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
            start_dt = lesson.start_time
            if not start_dt:
                continue

            end_dt = lesson.end_time or (start_dt + timedelta(minutes=lesson.duration_minutes or 90))
            type_key, color = _event_type_from_lesson(lesson)

            module = getattr(lesson, "module", None)
            course = getattr(module, "course", None)

            result.append(
                {
                    "lesson_id": str(lesson.id),
                    "course_name": course.course_name if course else "Khóa học",
                    "module_name": module.title if module else None,
                    "lesson_title": lesson.title or "Bài học",
                    "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "location": "Trực tuyến",
                    "color": color,
                    "type": type_key,
                    "type_label": TYPE_LABELS.get(type_key, "Sự kiện"),
                    "date_display": start_dt.strftime("%d/%m/%Y"),
                    "time_display": f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}",
                }
            )

        return result

    except Exception as exc:
        print("❌ [get_lesson_schedule] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_student_schedule(db: Session, user_id: str) -> list[dict]:
    """Gộp lịch bài học và lịch học định kỳ."""
    try:
        all_events = get_lesson_schedule(db, user_id) + get_class_schedules(db, user_id)
        return sorted(all_events, key=lambda item: item.get("start") or "")
    except Exception as exc:
        print("❌ [get_student_schedule] Lỗi:", exc)
        traceback.print_exc()
        return []


def get_schedule_list(db: Session, user_id: str) -> list[dict]:
    return get_student_schedule(db, user_id)


def get_schedule_by_date(db: Session, user_id: str, date: datetime) -> list[dict]:
    target_date = date.strftime("%Y-%m-%d")
    return [event for event in get_student_schedule(db, user_id) if event.get("start", "").startswith(target_date)]


def get_schedule_for_week(db: Session, user_id: str, start_date: datetime) -> list[dict]:
    """
    Lấy lịch trong 7 ngày, dùng điều kiện < ngày kết thúc để tránh dư 1 ngày.
    """
    end_date = start_date + timedelta(days=7)
    start_key = start_date.strftime("%Y-%m-%d")
    end_key = end_date.strftime("%Y-%m-%d")

    return [
        event for event in get_student_schedule(db, user_id)
        if start_key <= event.get("start", "")[:10] < end_key
    ]
