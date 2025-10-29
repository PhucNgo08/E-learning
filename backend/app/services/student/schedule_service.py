"""
============================================================
📅 SERVICE: STUDENT - SCHEDULE
Xử lý logic lấy thời khóa biểu, lịch học, và hiển thị dạng
calendar hoặc list cho sinh viên.
============================================================
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.classes import Class
from app.models.enrollment import Enrollment
from app.models.user import User

# ============================================================
# 🔍 1️⃣ LẤY LỊCH HỌC CỦA SINH VIÊN
# ============================================================
async def get_student_schedule(db: Session, user_id: str):
    """
    Lấy thời khóa biểu của sinh viên, gồm các buổi học trong tuần.
    Trả về list dict để hiển thị trên calendar hoặc list.html
    """
    try:
        # 🔹 Kiểm tra sinh viên tồn tại
        student = db.query(User).filter(User.id == user_id).first()
        if not student:
            return []

        # 🔹 Lấy danh sách khóa học sinh viên đã ghi danh
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == user_id).all()
        if not enrollments:
            return []

        course_ids = [e.course_id for e in enrollments]

        # 🔹 Lấy toàn bộ bài học (lesson) của các khóa đó
        lessons = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .join(Course, Module.course_id == Course.id)
            .filter(Course.id.in_(course_ids))
            .all()
        )

        # 🔹 Tạo danh sách kết quả
        schedule_data = []
        for lesson in lessons:
            # Nếu có trường lesson_date hoặc start_time → dùng, nếu không thì bỏ qua
            if hasattr(lesson, "lesson_date") and lesson.lesson_date:
                date_start = lesson.lesson_date
            elif hasattr(lesson, "created_at"):
                date_start = lesson.created_at
            else:
                continue

            # Xác định thời gian kết thúc tạm (giả sử 90 phút)
            date_end = date_start + timedelta(minutes=90)

            schedule_data.append({
                "lesson_id": lesson.id,
                "course_name": getattr(lesson.module.course, "title", "Không xác định"),
                "module_name": getattr(lesson.module, "title", "Module không tên"),
                "lesson_title": lesson.title,
                "start": date_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": date_end.strftime("%Y-%m-%dT%H:%M:%S"),
                "location": getattr(lesson, "location", "Trực tuyến"),
                "color": "#00bcd4" if "video" in lesson.title.lower() else "#4caf50",
            })

        return schedule_data

    except Exception as e:
        print(f"❌ Lỗi lấy lịch học sinh viên: {e}")
        return []


# ============================================================
# 🗓️ 2️⃣ LẤY LỊCH THEO NGÀY HOẶC TUẦN
# ============================================================
async def get_schedule_by_date(db: Session, user_id: str, date: datetime):
    """Lấy danh sách buổi học trong ngày cụ thể"""
    all_schedule = await get_student_schedule(db, user_id)
    date_str = date.strftime("%Y-%m-%d")

    return [
        s for s in all_schedule
        if s["start"].startswith(date_str)
    ]


# ============================================================
# 📋 3️⃣ LẤY DANH SÁCH CHO LIST.HTML
# ============================================================
async def get_schedule_list(db: Session, user_id: str):
    """Trả về danh sách buổi học dạng list để hiển thị trên trang list.html"""
    all_schedule = await get_student_schedule(db, user_id)

    # Sắp xếp theo ngày học tăng dần
    sorted_schedule = sorted(all_schedule, key=lambda x: x["start"])
    for s in sorted_schedule:
        s["date_display"] = datetime.strptime(s["start"], "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y %H:%M")

    return sorted_schedule
