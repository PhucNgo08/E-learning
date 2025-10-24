from sqlalchemy.orm import Session
from app.models.class_schedule import ClassSchedule
from app.models.course_section import CourseSection
from app.models.course import Course
from datetime import time

# =========================================================
# 🧭 Ánh xạ thứ trong tuần sang tiếng Việt
# =========================================================
DAY_MAP = {
    "monday": "Thứ 2",
    "tuesday": "Thứ 3",
    "wednesday": "Thứ 4",
    "thursday": "Thứ 5",
    "friday": "Thứ 6",
    "saturday": "Thứ 7",
    "sunday": "Chủ nhật",
}

# =========================================================
# 🗓️ Hàm: Lấy lịch dạy của giáo viên
# =========================================================
def get_teacher_schedule(db: Session, teacher_id: str):
    """
    Lấy lịch dạy của một giáo viên cụ thể.
    Tham số:
        db          : phiên kết nối DB
        teacher_id  : ID của giáo viên (users.id)
    """
    try:
        # 🔹 Truy vấn join 3 bảng: class_schedules → course_sections → courses
        results = (
            db.query(
                Course.course_name,
                CourseSection.section_name,
                ClassSchedule.day_of_week,
                ClassSchedule.start_time,
                ClassSchedule.end_time,
                ClassSchedule.room_number,
            )
            .join(CourseSection, CourseSection.id == ClassSchedule.section_id)
            .join(Course, Course.id == CourseSection.course_id)
            .filter(CourseSection.teacher_id == teacher_id)
            .order_by(ClassSchedule.day_of_week, ClassSchedule.start_time)
            .all()
        )

        # 🔹 Chuyển đổi kết quả thành danh sách dictionary dễ render
        schedule = []
        for row in results:
            day_vn = DAY_MAP.get(row.day_of_week, row.day_of_week)
            start = row.start_time.strftime("%H:%M") if isinstance(row.start_time, time) else str(row.start_time)
            end = row.end_time.strftime("%H:%M") if isinstance(row.end_time, time) else str(row.end_time)
            schedule.append({
                "day": day_vn,
                "time": f"{start} - {end}",
                "course_name": row.course_name,
                "section_name": row.section_name,
                "room_number": row.room_number or "—"
            })

        return schedule

    except Exception as e:
        print(f"[❌ ERROR] get_teacher_schedule: {e}")
        return []
