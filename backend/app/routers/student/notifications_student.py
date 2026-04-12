"""
==========================================================
🎓 ROUTER: Student - Notifications (SYNC FIXED)
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

router = APIRouter(
    prefix="/student/notifications",
    tags=["Student - Notifications"]
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


@router.get("/", response_class=HTMLResponse)
async def list_notifications(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
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
        return HTMLResponse("<h4>❌ Lỗi khi tải thông báo.</h4>", status_code=500)


@router.get("/detail/{notification_id}", response_class=HTMLResponse)
async def notification_detail(request: Request, notification_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        notification = notification_service.get_notification_detail(db, notification_id, user_id)

        if not notification:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy thông báo."},
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
        return HTMLResponse("<h4>❌ Lỗi khi xem chi tiết.</h4>", status_code=500)


@router.get("/read/{notification_id}")
async def mark_as_read(request: Request, notification_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        result = notification_service.mark_as_read(db, notification_id, user_id)

        if not result:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Không có quyền."},
                status_code=403,
            )

        return RedirectResponse("/student/notifications", status.HTTP_303_SEE_OTHER)

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi đánh dấu đã đọc.</h4>", status_code=500)


@router.get("/toggle/{notification_id}")
async def toggle_read(request: Request, notification_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        result = notification_service.toggle_read_status(db, notification_id, user_id)

        if not result:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Không thể cập nhật trạng thái."},
                status_code=403,
            )

        return RedirectResponse("/student/notifications", status.HTTP_303_SEE_OTHER)

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi toggle trạng thái.</h4>", status_code=500)


@router.get("/read_all", response_class=HTMLResponse)
async def mark_all_as_read(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        count = notification_service.mark_all_as_read(db, user_id)

        return templates["student"].TemplateResponse(
            "notifications/read_all_done.html",
            {
                "request": request,
                "count": count,
                "message": "Tất cả thông báo đã được đánh dấu là đã đọc.",
                "page_title": "🔔 Đã đọc tất cả",
                "active_page": "notifications",
            },
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi đánh dấu tất cả.</h4>", status_code=500)


@router.get("/delete/{notification_id}", response_class=HTMLResponse)
async def delete_notification_confirm(request: Request, notification_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        notification = notification_service.get_notification_for_user(db, notification_id, user_id)

        if not notification:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy thông báo."},
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "notifications/delete_confirm.html",
            {
                "request": request,
                "notification": notification,
                "page_title": "🗑️ Xóa thông báo",
                "active_page": "notifications",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi tải trang xác nhận xóa.</h4>", status_code=500)


@router.post("/delete/{notification_id}")
async def delete_notification(request: Request, notification_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        success = notification_service.delete_notification(db, notification_id, user_id)

        if not success:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Không có quyền xóa."},
                status_code=403,
            )

        return RedirectResponse("/student/notifications", status.HTTP_303_SEE_OTHER)

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi xóa thông báo.</h4>", status_code=500)


@router.get("/delete_all", response_class=HTMLResponse)
async def delete_all(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
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
        return HTMLResponse("<h4>❌ Lỗi khi xóa tất cả.</h4>", status_code=500)


@router.get("/settings", response_class=HTMLResponse)
async def notification_settings(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
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
        return HTMLResponse("<h4>❌ Lỗi tải cài đặt.</h4>", status_code=500)


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
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
        return HTMLResponse("<h4>❌ Lỗi lưu cài đặt.</h4>", status_code=500)
