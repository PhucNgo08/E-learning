"""
==========================================================
🗓️ SERVICE: Teacher - Schedule
Lấy danh sách lịch dạy của giáo viên (theo tuần / khóa học / buổi)
==========================================================
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson


def get_teacher_schedule(db: Session, teacher_id: str):
    """Trả về lịch dạy của giáo viên (theo tuần hiện tại)"""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(
            Course.teacher_id == teacher_id,
            Lesson.start_time >= start_of_week,
            Lesson.start_time <= end_of_week,
        )
        .order_by(Lesson.start_time.asc())
        .all()
    )

    schedule_by_day = {}
    for lesson in lessons:
        date_key = (lesson.start_time + timedelta(hours=7)).strftime("%Y-%m-%d")
        schedule_by_day.setdefault(date_key, []).append({
            "course_name": lesson.module.course.course_name,
            "module_title": lesson.module.title,
            "lesson_title": lesson.title,
            "start_time": lesson.start_time,
            "end_time": lesson.end_time,
        })

    result = []
    for i in range(7):
        date = start_of_week + timedelta(days=i)
        date_key = date.strftime("%Y-%m-%d")
        result.append({
            "date": date.strftime("%A (%d/%m)"),
            "lessons": schedule_by_day.get(date_key, [])
        })

    return {
        "week_start": start_of_week.strftime("%d/%m/%Y"),
        "week_end": end_of_week.strftime("%d/%m/%Y"),
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
        .filter(
            Course.teacher_id == teacher_id,
            Lesson.start_time >= start_date,
            Lesson.start_time < end_date,
        )
        .order_by(Lesson.start_time.asc())
        .all()
    )

    schedule = {}
    for lesson in lessons:
        key = lesson.start_time.strftime("%Y-%m-%d")
        schedule.setdefault(key, []).append({
            "course_name": lesson.module.course.course_name,
            "lesson_title": lesson.title,
            "start_time": lesson.start_time,
            "end_time": lesson.end_time,
        })

    return schedule
