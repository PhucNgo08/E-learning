"""
==========================================================
📅 ROUTER: Teacher - Schedule Management
Quản lý lịch giảng dạy theo tuần và theo tháng cho giáo viên
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

# ✅ Import nội bộ
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path
from app.services.teacher import schedule_service

# ======================================================
# ⚙️ Router
# ======================================================
router = APIRouter(
    prefix="/teacher/schedule",
    tags=["Teacher - Schedule"]
)

# ======================================================
# 🧭 0️⃣ Redirect gốc → /list
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root():
    """Chuyển /teacher/schedule → /teacher/schedule/list"""
    return RedirectResponse("/teacher/schedule/list", status_code=303)


# ======================================================
# 📆 1️⃣ Lịch dạy theo tuần
# ======================================================
@router.get("/list", response_class=HTMLResponse)
def list_schedule_week(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """
    Hiển thị lịch giảng dạy trong tuần của giáo viên.
    Bao gồm thông tin khóa học, module, bài học, và thời gian.
    """
    teacher = current_teacher
    schedule = schedule_service.get_teacher_schedule(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "schedule/list.html",
        {
            "request": request,
            "teacher": teacher,
            "schedule": schedule["days"],
            "week_start": schedule["week_start"],
            "week_end": schedule["week_end"],
            "page_title": "📅 Lịch dạy trong tuần",
            "now": datetime.now(),
        },
    )


# ======================================================
# 🗓️ 2️⃣ Lịch dạy theo tháng (FullCalendar)
# ======================================================
@router.get("/calendar", response_class=HTMLResponse)
def view_calendar_month(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """
    Hiển thị lịch giảng dạy của giáo viên theo dạng FullCalendar (tháng hiện tại)
    """
    teacher = current_teacher

    # 🔹 Lấy dữ liệu lịch tháng
    schedule = schedule_service.get_teacher_schedule_month(
        db,
        teacher.id,
        month=datetime.now().month,
        year=datetime.now().year,
    )

    # 🔹 Chuẩn bị dữ liệu cho FullCalendar
    events = []
    for date, lessons in schedule.items():
        for lesson in lessons:
            events.append({
                "title": f"{lesson['course_name']} - {lesson['lesson_title']}",
                "start": f"{date}T{lesson['start_time'].strftime('%H:%M')}",
                "end": f"{date}T{lesson['end_time'].strftime('%H:%M')}",
            })

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "schedule/schedule.html",
        {
            "request": request,
            "teacher": teacher,
            "events": events,
            "month": datetime.now().month,
            "year": datetime.now().year,
            "page_title": "🗓️ Lịch dạy theo tháng (FullCalendar)",
        },
    )
