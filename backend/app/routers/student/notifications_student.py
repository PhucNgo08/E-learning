"""
==========================================================
🎓 ROUTER: Student - Notifications
Quản lý thông báo cá nhân của sinh viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import notification_service

router = APIRouter(prefix="/student/notifications", tags=["Student - Notifications"])


# ======================================================
# 🏠 1️⃣ Danh sách thông báo
# ======================================================
@router.get("/", response_class=HTMLResponse, name="student_notifications_list")
async def list_notifications(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    notifications = notification_service.get_student_notifications(db, user_id)

    return templates["student"].TemplateResponse(
        "notifications/list.html",
        {"request": request, "notifications": notifications, "active_page": "notifications"},
    )


# ======================================================
# 🔍 2️⃣ Xem chi tiết 1 thông báo
# ======================================================
@router.get("/{notification_id}", response_class=HTMLResponse, name="student_notification_detail")
async def notification_detail(request: Request, notification_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    notification = notification_service.get_notification_by_id(db, notification_id)
    if not notification or notification.user_id != user_id:
        return HTMLResponse("<h4>Không tìm thấy thông báo.</h4>", status_code=404)

    # 🔹 Đánh dấu đã đọc
    notification_service.mark_as_read(db, notification_id)

    return templates["student"].TemplateResponse(
        "notifications/detail.html",
        {"request": request, "notification": notification, "active_page": "notifications"},
    )


# ======================================================
# ⚙️ 3️⃣ Trang cài đặt thông báo
# ======================================================
@router.get("/settings", response_class=HTMLResponse, name="student_notification_settings")
async def notification_settings(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    settings = notification_service.get_user_notification_settings(db, user_id)

    return templates["student"].TemplateResponse(
        "notifications/notifications_settings.html",
        {"request": request, "settings": settings, "active_page": "notifications"},
    )
