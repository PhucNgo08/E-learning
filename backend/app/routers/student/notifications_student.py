"""
==========================================================
🎓 ROUTER: Student - Notifications (FULL 100%)
Hoàn thiện toàn bộ chức năng thông báo cho học viên:
- Danh sách
- Chi tiết (auto mark read)
- Đánh dấu đã đọc
- Đánh dấu tất cả
- Xóa 1 / xóa tất cả
- Cài đặt thông báo
- Toggle trạng thái đã đọc
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
import traceback

from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import notification_service


# ======================================================
# ⚙️ Router Config
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
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        notifications = notification_service.get_user_notifications(db, user_id)
        unread_count = notification_service.count_unread_notifications(db, user_id)

        return templates["student"].TemplateResponse(
            "notifications/list.html",
            {
                "request": request,
                "notifications": notifications,
                "unread_count": unread_count,
                "page_title": "🔔 Thông báo cá nhân",
                "active_page": "notifications",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi tải thông báo.</h4>", 500)


# ======================================================
# 🔍 2️⃣ Xem chi tiết (auto đánh dấu đã đọc)
# ======================================================
@router.get("/detail/{notification_id}", response_class=HTMLResponse)
async def notification_detail(request: Request, notification_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        # Lấy chi tiết + auto mark read
        notification = notification_service.get_notification_detail(db, notification_id, user_id)

        if not notification:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy thông báo hoặc bạn không có quyền truy cập."},
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "notifications/detail.html",
            {
                "request": request,
                "notification": notification,
                "page_title": "📄 Chi tiết thông báo",
                "active_page": "notifications",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi xem chi tiết.</h4>", 500)


# ======================================================
# 👁️ 3️⃣ Đánh dấu 1 thông báo đã đọc
# ======================================================
@router.get("/read/{notification_id}")
async def mark_as_read(request: Request, notification_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        result = notification_service.mark_as_read(db, notification_id, user_id)

        if not result:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Không tìm thấy hoặc bạn không có quyền."},
                status_code=403,
            )

        return RedirectResponse("/student/notifications", status.HTTP_303_SEE_OTHER)

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi đánh dấu đã đọc.</h4>", 500)


# ======================================================
# 🔁 4️⃣ Toggle trạng thái đã đọc ↔ chưa đọc
# ======================================================
@router.get("/toggle/{notification_id}")
async def toggle_read(request: Request, notification_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        result = notification_service.toggle_read_status(db, notification_id, user_id)

        if not result:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Không có quyền thao tác."},
                status_code=403,
            )

        return RedirectResponse("/student/notifications", status.HTTP_303_SEE_OTHER)

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi toggle trạng thái.</h4>", 500)


# ======================================================
# 🧹 5️⃣ Đánh dấu tất cả đã đọc
# ======================================================
@router.get("/read_all", response_class=HTMLResponse)
async def mark_all_as_read(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        count = notification_service.mark_all_as_read(db, user_id)

        return templates["student"].TemplateResponse(
            "notifications/read_all_done.html",
            {
                "request": request,
                "count": count,
                "page_title": "🔔 Đã đọc tất cả",
                "active_page": "notifications",
            },
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi đánh dấu tất cả.</h4>", 500)


# ======================================================
# 🗑️ 6️⃣ Xóa 1 thông báo
# ======================================================
@router.get("/delete/{notification_id}")
async def delete_notification(request: Request, notification_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        success = notification_service.delete_notification(db, notification_id, user_id)

        if not success:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền xóa thông báo này."},
                status_code=403,
            )

        return RedirectResponse("/student/notifications", status.HTTP_303_SEE_OTHER)

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi xóa thông báo.</h4>", 500)


# ======================================================
# 🗑️⚠️ 7️⃣ Xóa toàn bộ thông báo
# ======================================================
@router.get("/delete_all")
async def delete_all(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        count = notification_service.delete_all_notifications(db, user_id)

        return templates["student"].TemplateResponse(
            "notifications/delete_all_done.html",
            {
                "request": request,
                "count": count,
                "page_title": "🗑️ Xóa toàn bộ thông báo",
                "active_page": "notifications",
            },
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi xóa tất cả thông báo.</h4>", 500)


# ======================================================
# ⚙️ 8️⃣ Trang cài đặt thông báo
# ======================================================
@router.get("/settings", response_class=HTMLResponse)
async def notification_settings(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

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

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi tải cài đặt.</h4>", 500)


# ======================================================
# 💾 9️⃣ Lưu cài đặt thông báo
# ======================================================
@router.post("/settings", response_class=HTMLResponse)
async def update_settings(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        form = await request.form()

        new_settings = {
            "system": "system" in form,
            "course": "course" in form,
            "assignment": "assignment" in form,
            "quiz": "quiz" in form,
            "message": "message" in form,
        }

        notification_service.update_user_notification_settings(db, user_id, new_settings)

        return templates["student"].TemplateResponse(
            "notifications/settings.html",
            {
                "request": request,
                "settings": new_settings,
                "message": "✔ Đã lưu cài đặt.",
                "page_title": "⚙️ Cài đặt thông báo",
                "active_page": "notifications",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi lưu cài đặt.</h4>", 500)
