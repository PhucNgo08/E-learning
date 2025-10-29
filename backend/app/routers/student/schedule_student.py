from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.student import schedule_service
from app.dependencies.auth import get_current_student
from app.config.template_config import get_template_by_path  # ✅ Dùng template chung

router = APIRouter(prefix="/student/schedule", tags=["Student - Schedule"])

# ============================================================
# 🏠 0️⃣ Trang mặc định — chuyển hướng sang Calendar
# ============================================================
@router.get("/", response_class=HTMLResponse)
async def schedule_redirect():
    """Khi truy cập /student/schedule, tự động chuyển sang /calendar"""
    return RedirectResponse(url="/student/schedule/calendar")

# ============================================================
# 🗓️ 1️⃣ Xem lịch học dạng Calendar
# ============================================================
@router.get("/calendar", response_class=HTMLResponse)
async def view_calendar(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    """Hiển thị lịch học dạng calendar cho sinh viên"""
    tpl = get_template_by_path(request.url.path)  # ✅ Lấy template phù hợp (/student → student)
    schedule = await schedule_service.get_student_schedule(db, current_user.id)

    return tpl.TemplateResponse(
        "schedule/calendar.html",  # ✅ KHÔNG có 'student/' ở đầu
        {
            "request": request,
            "schedule": schedule,
            "student": current_user,
            "page_title": "🗓️ Lịch học & Kiểm tra"
        }
    )

# ============================================================
# 📋 2️⃣ Xem lịch học dạng danh sách
# ============================================================
@router.get("/list", response_class=HTMLResponse)
async def view_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    """Hiển thị lịch học dạng danh sách"""
    tpl = get_template_by_path(request.url.path)
    schedule = await schedule_service.get_schedule_list(db, current_user.id)

    return tpl.TemplateResponse(
        "schedule/list.html",  # ✅ KHÔNG có 'student/' ở đầu
        {
            "request": request,
            "schedules": schedule,
            "student": current_user,
            "page_title": "📋 Lịch học dạng danh sách"
        }
    )
