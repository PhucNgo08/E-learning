from __future__ import annotations

from datetime import datetime, timedelta
from calendar import monthrange

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.class_schedule import ClassSchedule
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.lesson import Lesson
from app.models.module import Module


VI_DAYS = [
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Chủ Nhật" if False else "Thứ Bảy",
    "Chủ Nhật",
]

DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _start_of_week(value: datetime | None = None) -> datetime:
    today = value or datetime.now()
    return datetime(today.year, today.month, today.day) - timedelta(days=today.weekday())


def _get_teacher_lesson_items(db: Session, teacher_id: str, start_date: datetime, end_date: datetime) -> list[dict]:
    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(
            Course.teacher_id == teacher_id,
            Course.status == "published",
            Module.is_published == 1,
            Lesson.is_published == 1,
            Lesson.start_time.isnot(None),
            Lesson.start_time >= start_date,
            Lesson.start_time < end_date,
        )
        .order_by(Lesson.start_time.asc())
        .all()
    )

    items: list[dict] = []
    for lesson in lessons:
        module = getattr(lesson, "module", None)
        course = getattr(module, "course", None)
        start_dt = lesson.start_time
        end_dt = lesson.end_time or (start_dt + timedelta(minutes=lesson.duration_minutes or 90))

        items.append(
            {
                "course_name": course.course_name if course else "Khóa học",
                "module_title": module.title if module else "—",
                "lesson_title": lesson.title or "Bài học",
                "start_time": start_dt,
                "end_time": end_dt,
                "location": "Trực tuyến",
                "event_type": "lesson",
            }
        )

    return items


def _get_teacher_class_schedule_rows(db: Session, teacher_id: str) -> list[ClassSchedule]:
    return (
        db.query(ClassSchedule)
        .join(CourseSection, CourseSection.id == ClassSchedule.section_id)
        .join(Course, Course.id == CourseSection.course_id)
        .options(joinedload(ClassSchedule.section).joinedload(CourseSection.course))
        .filter(
            Course.status == "published",
            or_(
                CourseSection.teacher_id == teacher_id,
                Course.teacher_id == teacher_id,
            ),
        )
        .order_by(ClassSchedule.day_of_week.asc(), ClassSchedule.start_time.asc())
        .all()
    )


def _class_schedule_to_item(schedule: ClassSchedule, date_value: datetime) -> dict | None:
    section = getattr(schedule, "section", None)
    course = getattr(section, "course", None)

    if not schedule.start_time or not schedule.end_time:
        return None

    start_dt = datetime.combine(date_value.date(), schedule.start_time)
    end_dt = datetime.combine(date_value.date(), schedule.end_time)

    section_code = getattr(section, "section_code", "") or ""
    section_name = getattr(section, "section_name", "") or ""

    title = f"Lịch học định kỳ {section_code}".strip()
    if section_name:
        title = f"{title} - {section_name}"

    location = f"{schedule.building or ''} {schedule.room_number or ''}".strip()
    if not location:
        location = getattr(section, "location", None) or "Tại lớp"

    return {
        "course_name": course.course_name if course else "Khóa học",
        "module_title": "Lịch học định kỳ",
        "lesson_title": title,
        "start_time": start_dt,
        "end_time": end_dt,
        "location": location,
        "event_type": "class_schedule",
    }


def _get_teacher_class_items_for_week(db: Session, teacher_id: str, start_week: datetime) -> list[dict]:
    rows = _get_teacher_class_schedule_rows(db, teacher_id)
    items: list[dict] = []

    for schedule in rows:
        day_index = DAY_MAP.get((schedule.day_of_week or "").lower())
        if day_index is None:
            continue

        date_value = start_week + timedelta(days=day_index)
        item = _class_schedule_to_item(schedule, date_value)
        if item:
            items.append(item)

    return items


def _iter_month_dates(year: int, month: int):
    total_days = monthrange(year, month)[1]
    for day in range(1, total_days + 1):
        yield datetime(year, month, day)


def _get_teacher_class_items_for_month(db: Session, teacher_id: str, month: int, year: int) -> list[dict]:
    rows = _get_teacher_class_schedule_rows(db, teacher_id)
    items: list[dict] = []

    dates_by_weekday: dict[int, list[datetime]] = {}
    for date_value in _iter_month_dates(year, month):
        dates_by_weekday.setdefault(date_value.weekday(), []).append(date_value)

    for schedule in rows:
        day_index = DAY_MAP.get((schedule.day_of_week or "").lower())
        if day_index is None:
            continue

        for date_value in dates_by_weekday.get(day_index, []):
            item = _class_schedule_to_item(schedule, date_value)
            if item:
                items.append(item)

    return items


def get_teacher_schedule(db: Session, teacher_id: str) -> dict:
    """Trả về lịch dạy của giáo viên trong tuần hiện tại."""
    start_week = _start_of_week()
    end_week = start_week + timedelta(days=7)

    lesson_items = _get_teacher_lesson_items(db, teacher_id, start_week, end_week)
    class_items = _get_teacher_class_items_for_week(db, teacher_id, start_week)

    schedule_by_day: dict[str, list[dict]] = {}
    for item in lesson_items + class_items:
        start_time = item.get("start_time")
        if not start_time:
            continue
        date_key = start_time.date().isoformat()
        schedule_by_day.setdefault(date_key, []).append(item)

    result_days = []
    for i in range(7):
        current_date = start_week + timedelta(days=i)
        date_key = current_date.date().isoformat()
        lessons = sorted(schedule_by_day.get(date_key, []), key=lambda item: item.get("start_time") or current_date)

        result_days.append(
            {
                "date_label": f"{VI_DAYS[current_date.weekday()]} ({current_date.strftime('%d/%m')})",
                "date_value": date_key,
                "lessons": lessons,
            }
        )

    return {
        "week_start": start_week.strftime("%d/%m/%Y"),
        "week_end": (end_week - timedelta(days=1)).strftime("%d/%m/%Y"),
        "days": result_days,
    }


def get_teacher_schedule_month(db: Session, teacher_id: str, month: int, year: int) -> list[dict]:
    """Trả về lịch dạy của giáo viên trong tháng."""
    if month < 1 or month > 12:
        month = datetime.now().month
    if year < 2000:
        year = datetime.now().year

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    lesson_items = _get_teacher_lesson_items(db, teacher_id, start_date, end_date)
    class_items = _get_teacher_class_items_for_month(db, teacher_id, month, year)

    results: list[dict] = []
    for item in sorted(lesson_items + class_items, key=lambda value: value.get("start_time") or start_date):
        start_time = item.get("start_time")
        end_time = item.get("end_time")

        results.append(
            {
                "course_name": item.get("course_name") or "Khóa học",
                "module_title": item.get("module_title") or "—",
                "lesson_title": item.get("lesson_title") or "Buổi học",
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "location": item.get("location") or "Trực tuyến",
                "event_type": item.get("event_type") or "lesson",
            }
        )

    return results
