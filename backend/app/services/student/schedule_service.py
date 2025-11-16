"""
============================================================
📅 SERVICE: STUDENT - SCHEDULE (FINAL 2025)
Tổng hợp lịch học: Lesson + ClassSchedule + Quiz/Exam
============================================================
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.enrollment import Enrollment
from app.models.course_section import CourseSection
from app.models.class_schedule import ClassSchedule
from app.models.user import User
import traceback


# ============================================================
# 🔍 1️⃣ LẤY LỊCH HỌC CHÍNH QUY THEO CLASS_SCHEDULES
# ============================================================
def get_class_schedules(db: Session, user_id: str):
    """
    Lấy lịch học theo tuần từ bảng class_schedules.
    (Thời khóa biểu chính quy)
    """
    try:
        enrolls = db.query(Enrollment).filter(
            Enrollment.user_id == user_id,
            Enrollment.enrollment_status.in_(["active", "approved"])
        ).all()

        if not enrolls:
            return []

        class_ids = [e.class_id for e in enrolls if e.class_id]

        # Lấy danh sách section của các class này
        sections = (
            db.query(CourseSection)
            .filter(CourseSection.id.in_(class_ids))
            .all()
        )
        if not sections:
            return []

        section_ids = [s.id for s in sections]

        schedules = db.query(ClassSchedule).filter(
            ClassSchedule.section_id.in_(section_ids)
        ).all()

        result = []
        for sch in schedules:

            # Convert day_of_week → số (monday = 0)
            day_map = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            dow = day_map.get(sch.day_of_week, 0)

            # tạo ngày tiếp theo của tuần
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            date_of_class = start_of_week + timedelta(days=dow)

            start_dt = datetime.combine(date_of_class.date(), sch.start_time)
            end_dt = datetime.combine(date_of_class.date(), sch.end_time)

            result.append({
                "course_name": getattr(sch.section.course, "course_name", "Lớp học"),
                "module_name": None,
                "lesson_title": "Lịch học định kỳ",
                "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "location": f"{sch.building or ''} {sch.room_number or ''}".strip() or "Tại lớp",
                "color": "#007bff",   # xanh dương – lịch chính quy
                "type": "class_schedule",
            })

        return result

    except Exception as e:
        print("❌ [get_class_schedules] Lỗi:", e)
        traceback.print_exc()
        return []


# ============================================================
# 🔍 2️⃣ LẤY LỊCH BÀI HỌC (LESSONS)
# ============================================================
def get_lesson_schedule(db: Session, user_id: str):

    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == user_id
    ).all()
    course_ids = [e.course_id for e in enrollments if e.course_id]

    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.id.in_(course_ids))
        .all()
    )

    result = []
    for lesson in lessons:

        # Lấy start_time từ database mới (có cột start_time, end_time)
        if lesson.start_time:
            start_dt = lesson.start_time
            end_dt = lesson.end_time or (start_dt + timedelta(minutes=90))
        else:
            continue

        # Xác định màu theo loại nội dung
        title = (lesson.title or "").lower()
        if "quiz" in title:
            color = "#ffc107"
            type_ = "quiz"
        elif "thi" in title or "exam" in title:
            color = "#ff4b5c"
            type_ = "exam"
        else:
            color = "#28a745"
            type_ = "lesson"

        result.append({
            "lesson_id": lesson.id,
            "course_name": lesson.module.course.course_name,
            "module_name": lesson.module.title,
            "lesson_title": lesson.title,
            "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": "Trực tuyến",
            "color": color,
            "type": type_,
        })

    return result


# ============================================================
# 🔥 3️⃣ TỔNG HỢP LỊCH (LESSON + CLASS_SCHEDULE)
# ============================================================
def get_student_schedule(db: Session, user_id: str):
    """Tổng hợp toàn bộ lịch học của sinh viên"""

    try:
        lesson_events = get_lesson_schedule(db, user_id)
        class_events = get_class_schedules(db, user_id)

        all_events = lesson_events + class_events
        sorted_events = sorted(all_events, key=lambda x: x["start"])

        print(f"📅 [Schedule] Total events for user={user_id}: {len(sorted_events)}")

        return sorted_events

    except Exception as e:
        print("❌ [get_student_schedule] Lỗi:", e)
        traceback.print_exc()
        return []


# ============================================================
# 📋 4️⃣ LIST VIEW
# ============================================================
def get_schedule_list(db: Session, user_id: str):
    data = get_student_schedule(db, user_id)

    for s in data:
        try:
            dt = datetime.strptime(s["start"], "%Y-%m-%dT%H:%M:%S")
            s["date_display"] = dt.strftime("%d/%m/%Y")
            s["time_display"] = dt.strftime("%H:%M")
        except:
            s["date_display"] = "-"
            s["time_display"] = "-"

    return data


# ============================================================
# 🗓️ 5️⃣ LỊCH THEO NGÀY
# ============================================================
def get_schedule_by_date(db: Session, user_id: str, date: datetime):
    all_events = get_student_schedule(db, user_id)
    d = date.strftime("%Y-%m-%d")
    return [e for e in all_events if e["start"].startswith(d)]


# ============================================================
# 📆 6️⃣ LỊCH THEO TUẦN
# ============================================================
def get_schedule_for_week(db: Session, user_id: str, start_date: datetime):

    end_date = start_date + timedelta(days=7)
    all_events = get_student_schedule(db, user_id)

    return [
        e for e in all_events
        if start_date.strftime("%Y-%m-%d") <= e["start"][:10] <= end_date.strftime("%Y-%m-%d")
    ]
