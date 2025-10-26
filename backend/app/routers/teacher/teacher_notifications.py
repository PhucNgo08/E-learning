"""
==========================================================
🔔 ROUTER: Teacher - Notifications
Hiển thị danh sách & chi tiết thông báo của giáo viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path
from app.services.teacher import notification_service


# =========================================================
# 🚀 Router
# =========================================================
router = APIRouter(
    prefix="/teacher/notifications",
    tags=["Teacher - Notifications"]
)


# =========================================================
# 🔔 1️⃣ Danh sách thông báo
# =========================================================
@router.get("/", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """
    Hiển thị danh sách thông báo của giáo viên hiện tại
    """
    teacher = current_teacher
    notifications = notification_service.get_notifications_by_user(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    print("📂 [DEBUG] Template loaded successfully.")

    return templates.TemplateResponse(
        "notifications/list.html",
        {
            "request": request,
            "teacher": teacher,
            "notifications": notifications,
            "page_title": "🔔 Thông báo của tôi",
        },
    )


# =========================================================
# 📄 2️⃣ Xem chi tiết thông báo
# =========================================================
@router.get("/detail/{notification_id}", response_class=HTMLResponse)
def detail_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """
    Xem chi tiết thông báo và đánh dấu là đã đọc
    """
    teacher = current_teacher
    notification = notification_service.get_notification_detail(db, notification_id, teacher.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")

    # ✅ Đánh dấu là đã đọc
    notification_service.mark_as_read(db, notification_id, teacher.id)

    # 🔗 Nếu có link đi kèm thì chuyển hướng
    if notification.link_url:
        return RedirectResponse(url=notification.link_url, status_code=303)

    templates = get_template_by_path(str(request.url.path))
    print("📂 [DEBUG] Template loaded successfully.")

    return templates.TemplateResponse(
        "notifications/detail.html",
        {
            "request": request,
            "teacher": teacher,
            "notification": notification,
            "page_title": f"📩 {notification.title}",
        },
    )
