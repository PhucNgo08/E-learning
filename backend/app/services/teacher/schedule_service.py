"""
==========================================================
🗓️ SERVICE: Teacher - Schedule
Lấy danh sách lịch dạy của giáo viên (theo tuần / tháng)
==========================================================
"""

from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta

from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson


def get_teacher_schedule(db: Session, teacher_id: str):
    """Trả về lịch dạy của giáo viên trong tuần hiện tại"""
    today = datetime.now()
    start_of_week = datetime(today.year, today.month, today.day) - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=7)

    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .options(
            joinedload(Lesson.module).joinedload(Module.course)
        )
        .filter(
            Course.teacher_id == teacher_id,
            Lesson.start_time.isnot(None),
            Lesson.start_time >= start_of_week,
            Lesson.start_time < end_of_week,
        )
        .order_by(Lesson.start_time.asc())
        .all()
    )

    schedule_by_day = {}
    for lesson in lessons:
        date_key = lesson.start_time.date().isoformat()
        schedule_by_day.setdefault(date_key, []).append({
            "course_name": lesson.module.course.course_name if lesson.module and lesson.module.course else "—",
            "module_title": lesson.module.title if lesson.module else "—",
            "lesson_title": lesson.title,
            "start_time": lesson.start_time,
            "end_time": lesson.end_time,
        })

    result = []
    for i in range(7):
        current_date = start_of_week + timedelta(days=i)
        date_key = current_date.date().isoformat()
        result.append({
            "date_label": current_date.strftime("%A (%d/%m)"),
            "date_value": date_key,
            "lessons": schedule_by_day.get(date_key, [])
        })

    return {
        "week_start": start_of_week.strftime("%d/%m/%Y"),
        "week_end": (end_of_week - timedelta(days=1)).strftime("%d/%m/%Y"),
        "days": result
    }


def get_teacher_schedule_month(db: Session, teacher_id: str, month: int, year: int):
    """Trả về lịch dạy của giáo viên trong tháng"""
    start_date = datetime(year, month, 1)
    end_date = datetime(year + (month == 12), (month % 12) + 1, 1)

    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .options(
            joinedload(Lesson.module).joinedload(Module.course)
        )
        .filter(
            Course.teacher_id == teacher_id,
            Lesson.start_time.isnot(None),
            Lesson.start_time >= start_date,
            Lesson.start_time < end_date,
        )
        .order_by(Lesson.start_time.asc())
        .all()
    )

    results = []
    for lesson in lessons:
        results.append({
            "course_name": lesson.module.course.course_name if lesson.module and lesson.module.course else "—",
            "module_title": lesson.module.title if lesson.module else "—",
            "lesson_title": lesson.title,
            "start_time": lesson.start_time.isoformat() if lesson.start_time else None,
            "end_time": lesson.end_time.isoformat() if lesson.end_time else None,
        })

    return results