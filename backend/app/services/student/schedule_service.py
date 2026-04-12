from datetime import datetime, timedelta
import traceback

from sqlalchemy.orm import Session, joinedload

from app.models.class_schedule import ClassSchedule
from app.models.course import Course
from app.models.course_section import CourseSection
from app.models.lesson import Lesson
from app.models.module import Module
from app.services.common.course_access_service import get_accessible_course_ids


def _get_accessible_course_ids(db: Session, user_id: str) -> list[str]:
    try:
        return list(get_accessible_course_ids(db, user_id))
    except Exception as e:
        print("❌ [_get_accessible_course_ids] Lỗi:", e)
        traceback.print_exc()
        return []


def get_class_schedules(db: Session, user_id: str):
    """
    Lấy lịch học định kỳ từ:
    course_enrollments -> course_sections -> class_schedules
    """
    try:
        course_ids = _get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        sections = (
            db.query(CourseSection)
            .options(joinedload(CourseSection.course))
            .filter(CourseSection.course_id.in_(course_ids))
            .all()
        )
        if not sections:
            return []

        section_ids = [s.id for s in sections]

        schedules = (
            db.query(ClassSchedule)
            .options(joinedload(ClassSchedule.section).joinedload(CourseSection.course))
            .filter(ClassSchedule.section_id.in_(section_ids))
            .all()
        )

        result = []
        day_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())

        for sch in schedules:
            dow = day_map.get((sch.day_of_week or "").lower(), 0)
            date_of_class = start_of_week + timedelta(days=dow)

            start_dt = datetime.combine(date_of_class.date(), sch.start_time)
            end_dt = datetime.combine(date_of_class.date(), sch.end_time)

            section = getattr(sch, "section", None)
            course = getattr(section, "course", None)

            result.append(
                {
                    "course_name": course.course_name if course else "Lớp học",
                    "module_name": None,
                    "lesson_title": f"Lịch học định kỳ - {getattr(section, 'section_code', '')}".strip(" -"),
                    "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "location": f"{sch.building or ''} {sch.room_number or ''}".strip() or "Tại lớp",
                    "color": "#0d6efd",
                    "type": "class_schedule",
                    "date_display": start_dt.strftime("%d/%m/%Y"),
                    "time_display": start_dt.strftime("%H:%M"),
                }
            )

        return result

    except Exception as e:
        print("❌ [get_class_schedules] Lỗi:", e)
        traceback.print_exc()
        return []


def get_lesson_schedule(db: Session, user_id: str):
    try:
        course_ids = _get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        lessons = (
            db.query(Lesson)
            .options(
                joinedload(Lesson.module).joinedload(Module.course)
            )
            .join(Module, Lesson.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .filter(Course.id.in_(course_ids))
            .all()
        )

        result = []

        for lesson in lessons:
            if not lesson.start_time:
                continue

            start_dt = lesson.start_time
            end_dt = lesson.end_time or (start_dt + timedelta(minutes=90))
            title = (lesson.title or "").lower()

            if "quiz" in title:
                color = "#ffc107"
                type_ = "quiz"
            elif "thi" in title or "exam" in title:
                color = "#dc3545"
                type_ = "exam"
            else:
                color = "#198754"
                type_ = "lesson"

            result.append(
                {
                    "lesson_id": lesson.id,
                    "course_name": lesson.module.course.course_name if lesson.module and lesson.module.course else "Khóa học",
                    "module_name": lesson.module.title if lesson.module else None,
                    "lesson_title": lesson.title,
                    "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                    "location": "Trực tuyến",
                    "color": color,
                    "type": type_,
                    "date_display": start_dt.strftime("%d/%m/%Y"),
                    "time_display": start_dt.strftime("%H:%M"),
                }
            )

        return result

    except Exception as e:
        print("❌ [get_lesson_schedule] Lỗi:", e)
        traceback.print_exc()
        return []


def get_student_schedule(db: Session, user_id: str):
    try:
        lesson_events = get_lesson_schedule(db, user_id)
        class_events = get_class_schedules(db, user_id)
        all_events = lesson_events + class_events
        return sorted(all_events, key=lambda x: x["start"])
    except Exception as e:
        print("❌ [get_student_schedule] Lỗi:", e)
        traceback.print_exc()
        return []


def get_schedule_list(db: Session, user_id: str):
    return get_student_schedule(db, user_id)


def get_schedule_by_date(db: Session, user_id: str, date: datetime):
    all_events = get_student_schedule(db, user_id)
    d = date.strftime("%Y-%m-%d")
    return [e for e in all_events if e["start"].startswith(d)]


def get_schedule_for_week(db: Session, user_id: str, start_date: datetime):
    end_date = start_date + timedelta(days=7)
    all_events = get_student_schedule(db, user_id)
    return [
        e for e in all_events
        if start_date.strftime("%Y-%m-%d") <= e["start"][:10] <= end_date.strftime("%Y-%m-%d")
    ]