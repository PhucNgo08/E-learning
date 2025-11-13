"""
==========================================================
🎓 ROUTER: Student - Notifications
Hoàn thiện đầy đủ chức năng quản lý thông báo cá nhân
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
import traceback

from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import notification_service


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/student/notifications",
    tags=["Student - Notifications"]
)


# ======================================================
# 🏠 1️⃣ Danh sách thông báo
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def list_notifications(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách thông báo của sinh viên."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        notifications = notification_service.get_student_notifications(db, user_id)
        return templates["student"].TemplateResponse(
            "notifications/list.html",
            {
                "request": request,
                "notifications": notifications,
                "page_title": "🔔 Thông báo cá nhân",
                "active_page": "notifications",
            },
        )
    except Exception as e:
        print("❌ [Notification][List] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách thông báo.</h4>", status_code=500)


# ======================================================
# 🔍 2️⃣ Xem chi tiết thông báo (và đánh dấu đã đọc)
# ======================================================
@router.get("/detail/{notification_id}", response_class=HTMLResponse)
async def notification_detail(request: Request, notification_id: str, db: Session = Depends(get_db)):
    """Xem chi tiết 1 thông báo."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        notification = notification_service.get_notification_by_id(db, notification_id)
        if not notification or notification.user_id != user_id:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy thông báo hoặc bạn không có quyền truy cập."},
                status_code=404,
            )

        # ✅ Đánh dấu đã đọc
        notification_service.mark_as_read(db, notification_id)

        return templates["student"].TemplateResponse(
            "notifications/detail.html",
            {
                "request": request,
                "notification": notification,
                "page_title": "📄 Chi tiết thông báo",
                "active_page": "notifications",
            },
        )
    except Exception as e:
        print("❌ [Notification][Detail] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xem chi tiết thông báo.</h4>", status_code=500)


# ======================================================
# ✅ 3️⃣ Đánh dấu 1 thông báo là đã đọc
# ======================================================
@router.get("/read/{notification_id}")
async def mark_as_read(request: Request, notification_id: str, db: Session = Depends(get_db)):
    """Đánh dấu 1 thông báo là đã đọc."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        notification = notification_service.get_notification_by_id(db, notification_id)
        if not notification or notification.user_id != user_id:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền cập nhật thông báo này."},
                status_code=403,
            )

        notification_service.mark_as_read(db, notification_id)
        print(f"✅ [Notification][MarkRead] user={user_id}, id={notification_id}")

        return RedirectResponse(url="/student/notifications", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        db.rollback()
        print("❌ [Notification][MarkRead] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi đánh dấu thông báo đã đọc.</h4>", status_code=500)


# ======================================================
# 🧹 4️⃣ Đánh dấu tất cả đã đọc
# ======================================================
@router.get("/read_all", response_class=HTMLResponse)
async def mark_all_as_read(request: Request, db: Session = Depends(get_db)):
    """Đánh dấu tất cả thông báo của sinh viên là đã đọc."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        count = notification_service.mark_all_as_read(db, user_id)
        print(f"✅ [Notification][MarkAll] user={user_id}, count={count}")

        message = f"✅ Đã đánh dấu {count} thông báo là đã đọc."
        return templates["student"].TemplateResponse(
            "notifications/read_all_done.html",
            {
                "request": request,
                "message": message,
                "page_title": "🔔 Đã đọc tất cả thông báo",
                "active_page": "notifications",
            },
        )
    except Exception as e:
        db.rollback()
        print("❌ [Notification][MarkAll] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi đánh dấu tất cả thông báo.</h4>", status_code=500)


# ======================================================
# 🗑️ 5️⃣ Xóa 1 thông báo
# ======================================================
@router.get("/delete/{notification_id}")
async def delete_notification(request: Request, notification_id: str, db: Session = Depends(get_db)):
    """Xóa một thông báo cá nhân."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        success = notification_service.delete_notification(db, notification_id, user_id)
        if not success:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền xóa thông báo này."},
                status_code=403,
            )

        print(f"🗑️ [Notification][Delete] user={user_id}, id={notification_id}")
        return RedirectResponse(url="/student/notifications", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        db.rollback()
        print("❌ [Notification][Delete] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xóa thông báo.</h4>", status_code=500)


# ======================================================
# ⚙️ 6️⃣ Trang cài đặt thông báo
# ======================================================
@router.get("/settings", response_class=HTMLResponse)
async def notification_settings(request: Request, db: Session = Depends(get_db)):
    """Trang cài đặt thông báo cá nhân."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        settings = notification_service.get_user_notification_settings(db, user_id)
        return templates["student"].TemplateResponse(
            "notifications/settings.html",
            {
                "request": request,
                "settings": settings,
                "page_title": "⚙️ Cài đặt thông báo",
                "active_page": "notifications",
            },
        )
    except Exception as e:
        print("❌ [Notification][Settings] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải trang cài đặt thông báo.</h4>", status_code=500)
