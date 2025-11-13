"""
==========================================================
🔔 ROUTER: Admin - Notification Management (v3.1 Final)
Quản lý và gửi thông báo hệ thống (CRUD + Template + Safe)
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

# ✅ Import nội bộ
from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin
from app.models.notification import Notification
from app.models.user import User

# ======================================================
# ⚙️ Router
# ======================================================
router = APIRouter(
    prefix="/admin/notification",
    tags=["Admin - Notification Management"],
)


# ======================================================
# 📋 1️⃣ Danh sách thông báo
# ======================================================
@router.get("/list", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Hiển thị danh sách thông báo"""
    try:
        tpl = get_template_by_path(request.url.path)

        notifications = (
            db.query(Notification)
            .order_by(Notification.created_at.desc())
            .all()
        )
        user_map = {u.id: u.full_name for u in db.query(User).all()}
        total = len(notifications)

        return tpl.TemplateResponse(
            "notification/list.html",  # ✅ chuẩn hóa đường dẫn
            {
                "request": request,
                "notifications": notifications,
                "user_map": user_map,
                "total": total,
                "page_title": "🔔 Quản lý Thông báo",
                "active_page": "notification",
            },
        )
    except Exception as e:
        print("❌ Lỗi khi load danh sách thông báo:", e)
        traceback.print_exc()
        return HTMLResponse(
            f"<pre style='color:red'>{traceback.format_exc()}</pre>",
            status_code=500,
        )


# ======================================================
# 📨 2️⃣ Trang tạo thông báo mới (GET)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
def create_notification_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Hiển thị form tạo thông báo"""
    tpl = get_template_by_path(request.url.path)
    users = db.query(User).order_by(User.full_name).all()

    return tpl.TemplateResponse(
        "notification/create.html",
        {
            "request": request,
            "users": users,
            "page_title": "📨 Gửi thông báo mới",
            "active_page": "notification",
        },
    )


# ======================================================
# 📨 3️⃣ Gửi thông báo mới (POST)
# ======================================================
@router.post("/create")
def create_notification_action(
    user_id: str = Form(...),
    title: str = Form(...),
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Xử lý tạo thông báo"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

        new_notification = Notification(
            user_id=user_id,
            title=title.strip(),
            message=message.strip(),
            created_at=datetime.now(),
        )
        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

        return RedirectResponse(url="/admin/notification/list", status_code=303)

    except Exception as e:
        print("❌ Lỗi khi tạo thông báo:", e)
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# 🗑️ 4️⃣ Xóa thông báo
# ======================================================
@router.get("/delete/{notification_id}", response_class=HTMLResponse)
def confirm_delete_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Hiển thị trang xác nhận xóa"""
    tpl = get_template_by_path(request.url.path)
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")

    user = db.query(User).filter(User.id == notification.user_id).first()

    return tpl.TemplateResponse(
        "notification/delete.html",
        {
            "request": request,
            "notification": notification,
            "user": user,
            "page_title": "🗑️ Xóa Thông báo",
            "active_page": "notification",
        },
    )


@router.post("/delete/{notification_id}")
def delete_notification_action(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Xóa thông báo"""
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")

        db.delete(notification)
        db.commit()
        return RedirectResponse(url="/admin/notification/list", status_code=303)
    except Exception as e:
        print("❌ Lỗi khi xóa thông báo:", e)
        db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
