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
from app.models.enrollment import Enrollment
from app.models.user import User
import traceback


# ============================================================
# 🔍 1️⃣ LẤY LỊCH HỌC CỦA SINH VIÊN
# ============================================================
def get_student_schedule(db: Session, user_id: str):
    """
    Lấy thời khóa biểu của sinh viên, gồm các buổi học trong tuần.
    Trả về list dict để hiển thị trên calendar hoặc list.html
    """
    try:
        # 🔹 Kiểm tra sinh viên tồn tại
        student = db.query(User).filter(User.id == user_id).first()
        if not student:
            print(f"⚠️ [Schedule] Không tìm thấy sinh viên ID={user_id}")
            return []

        # 🔹 Lấy danh sách khóa học sinh viên đã ghi danh
        enrollments = db.query(Enrollment).filter(Enrollment.user_id == user_id).all()
        if not enrollments:
            print(f"ℹ️ [Schedule] Sinh viên {student.full_name} chưa ghi danh khóa học nào.")
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

        if not lessons:
            print(f"ℹ️ [Schedule] Không tìm thấy bài học cho user_id={user_id}")
            return []

        # 🔹 Chuẩn bị danh sách kết quả
        schedule_data = []
        for lesson in lessons:
            # Xác định ngày bắt đầu (ưu tiên lesson_date nếu có)
            if hasattr(lesson, "lesson_date") and lesson.lesson_date:
                date_start = lesson.lesson_date
            elif hasattr(lesson, "created_at") and lesson.created_at:
                date_start = lesson.created_at
            else:
                continue

            # Thời lượng mặc định: 90 phút
            date_end = date_start + timedelta(minutes=90)

            # Màu sắc và loại bài học
            title_lower = (lesson.title or "").lower()
            if "quiz" in title_lower:
                color = "#ffc107"  # vàng
                type_ = "quiz"
            elif "thi" in title_lower or "exam" in title_lower:
                color = "#ff4b5c"  # đỏ
                type_ = "exam"
            else:
                color = "#28a745"  # xanh lá
                type_ = "lesson"

            # Đưa vào danh sách kết quả
            schedule_data.append({
                "lesson_id": lesson.id,
                "course_name": getattr(lesson.module.course, "title", "Không xác định"),
                "module_name": getattr(lesson.module, "title", "Module không tên"),
                "lesson_title": lesson.title,
                "start": date_start.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": date_end.strftime("%Y-%m-%dT%H:%M:%S"),
                "location": getattr(lesson, "location", "Trực tuyến"),
                "color": color,
                "type": type_,
            })

        print(f"✅ [Schedule] Found {len(schedule_data)} lessons for user={user_id}")
        return schedule_data

    except Exception as e:
        print("❌ [get_student_schedule] Lỗi:", e)
        traceback.print_exc()
        return []


# ============================================================
# 🗓️ 2️⃣ LẤY LỊCH THEO NGÀY
# ============================================================
def get_schedule_by_date(db: Session, user_id: str, date: datetime):
    """Lấy danh sách buổi học trong ngày cụ thể."""
    all_schedule = get_student_schedule(db, user_id)
    date_str = date.strftime("%Y-%m-%d")
    return [s for s in all_schedule if s["start"].startswith(date_str)]


# ============================================================
# 📋 3️⃣ LẤY DANH SÁCH CHO LIST.HTML
# ============================================================
def get_schedule_list(db: Session, user_id: str):
    """Trả về danh sách buổi học dạng list để hiển thị trên trang list.html."""
    all_schedule = get_student_schedule(db, user_id)
    sorted_schedule = sorted(all_schedule, key=lambda x: x["start"])

    # Thêm định dạng hiển thị
    for s in sorted_schedule:
        try:
            dt = datetime.strptime(s["start"], "%Y-%m-%dT%H:%M:%S")
            s["date_display"] = dt.strftime("%d/%m/%Y")
            s["time_display"] = dt.strftime("%H:%M")
        except Exception:
            s["date_display"] = "-"
            s["time_display"] = "-"

    print(f"📋 [Schedule] Render list view for {len(sorted_schedule)} entries.")
    return sorted_schedule


# ============================================================
# 📆 4️⃣ LẤY LỊCH HỌC TRONG TUẦN
# ============================================================
def get_schedule_for_week(db: Session, user_id: str, start_date: datetime):
    """Lấy thời khóa biểu cho 1 tuần (7 ngày)."""
    end_date = start_date + timedelta(days=7)
    all_schedule = get_student_schedule(db, user_id)
    return [
        s for s in all_schedule
        if start_date.strftime("%Y-%m-%d") <= s["start"][:10] <= end_date.strftime("%Y-%m-%d")
    ]
