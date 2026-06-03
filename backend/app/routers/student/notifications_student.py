"""
==========================================================
🎓 ROUTER: Student - Notifications
Hiển thị thông báo sinh viên
- Danh sách
- Chi tiết
- Đánh dấu đã đọc
- Toggle đọc/chưa đọc
- Xóa 1 thông báo
- Xóa tất cả
- API summary cho chuông thông báo trên layout
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette import status
import traceback

from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import notification_service


router = APIRouter(
    prefix="/student/notifications",
    tags=["Student - Notifications"],
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")

    if not user_id or role != "student":
        return None

    return user_id


def render_student_template(
    template_name: str,
    request: Request,
    context: dict,
    status_code: int = 200,
):
    base_context = {
        "request": request,
        "active_page": "notifications",
    }
    base_context.update(context)

    return templates["student"].TemplateResponse(
        template_name,
        base_context,
        status_code=status_code,
    )


# ======================================================
# API SUMMARY CHO CHUÔNG THÔNG BÁO
# ======================================================
@router.get("/api/summary")
async def notification_summary(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return JSONResponse(
            {
                "authenticated": False,
                "unread_count": 0,
                "latest_notifications": [],
            }
        )

    try:
        unread_count = notification_service.count_unread_notifications(db, user_id)
        latest_notifications = notification_service.get_latest_notifications(
            db,
            user_id,
            limit=5,
        )

        data = []
        for n in latest_notifications:
            data.append(
                {
                    "id": n.id,
                    "title": n.title or "Thông báo",
                    "message": n.message or "",
                    "notification_type": n.notification_type or "system",
                    "is_read": bool(n.is_read),
                    "link_url": n.link_url,
                    "created_at": (
                        n.created_at.strftime("%d/%m/%Y %H:%M")
                        if n.created_at
                        else ""
                    ),
                }
            )

        return JSONResponse(
            {
                "authenticated": True,
                "unread_count": unread_count,
                "latest_notifications": data,
            }
        )

    except Exception:
        traceback.print_exc()
        return JSONResponse(
            {
                "authenticated": True,
                "unread_count": 0,
                "latest_notifications": [],
                "error": "Không tải được thông báo.",
            },
            status_code=500,
        )


# ======================================================
# LIST
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        notifications = notification_service.get_user_notifications(db, user_id)
        unread_count = notification_service.count_unread_notifications(db, user_id)

        return render_student_template(
            "notifications/list.html",
            request,
            {
                "notifications": notifications,
                "unread_count": unread_count,
                "page_title": "🔔 Thông báo cá nhân",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi tải thông báo.</h4>", status_code=500)


# ======================================================
# DETAIL
# ======================================================
@router.get("/detail/{notification_id}", response_class=HTMLResponse)
async def notification_detail(
    request: Request,
    notification_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        notification = notification_service.get_notification_detail(
            db,
            notification_id,
            user_id,
        )

        if not notification:
            return render_student_template(
                "error.html",
                request,
                {"message": "❌ Không tìm thấy thông báo."},
                status_code=404,
            )

        return render_student_template(
            "notifications/detail.html",
            request,
            {
                "notification": notification,
                "page_title": "📄 Chi tiết thông báo",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi xem chi tiết.</h4>", status_code=500)


# ======================================================
# READ
# ======================================================
@router.get("/read/{notification_id}")
async def mark_as_read(
    request: Request,
    notification_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        result = notification_service.mark_as_read(db, notification_id, user_id)

        if not result:
            return render_student_template(
                "error.html",
                request,
                {"message": "⚠️ Không có quyền hoặc không tìm thấy thông báo."},
                status_code=403,
            )

        return RedirectResponse(
            "/student/notifications/",
            status.HTTP_303_SEE_OTHER,
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi đánh dấu đã đọc.</h4>", status_code=500)


@router.get("/toggle/{notification_id}")
async def toggle_read(
    request: Request,
    notification_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        result = notification_service.toggle_read_status(
            db,
            notification_id,
            user_id,
        )

        if not result:
            return render_student_template(
                "error.html",
                request,
                {"message": "⚠️ Không thể cập nhật trạng thái thông báo."},
                status_code=403,
            )

        return RedirectResponse(
            "/student/notifications/",
            status.HTTP_303_SEE_OTHER,
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi toggle trạng thái.</h4>", status_code=500)


@router.get("/read_all", response_class=HTMLResponse)
async def mark_all_as_read(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        count = notification_service.mark_all_as_read(db, user_id)

        return render_student_template(
            "notifications/read_all_done.html",
            request,
            {
                "count": count,
                "message": "Tất cả thông báo đã được đánh dấu là đã đọc.",
                "page_title": "✅ Đã đọc tất cả",
            },
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi đánh dấu tất cả.</h4>", status_code=500)


# ======================================================
# DELETE
# ======================================================
@router.get("/delete/{notification_id}", response_class=HTMLResponse)
async def delete_notification_confirm(
    request: Request,
    notification_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        notification = notification_service.get_notification_for_user(
            db,
            notification_id,
            user_id,
        )

        if not notification:
            return render_student_template(
                "error.html",
                request,
                {"message": "❌ Không tìm thấy thông báo."},
                status_code=404,
            )

        return render_student_template(
            "notifications/delete_confirm.html",
            request,
            {
                "notification": notification,
                "page_title": "🗑️ Xóa thông báo",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse(
            "<h4>❌ Lỗi tải trang xác nhận xóa.</h4>",
            status_code=500,
        )


@router.post("/delete/{notification_id}")
async def delete_notification(
    request: Request,
    notification_id: str,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        success = notification_service.delete_notification(
            db,
            notification_id,
            user_id,
        )

        if not success:
            return render_student_template(
                "error.html",
                request,
                {"message": "⚠️ Không có quyền xóa thông báo."},
                status_code=403,
            )

        return RedirectResponse(
            "/student/notifications/",
            status.HTTP_303_SEE_OTHER,
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi xóa thông báo.</h4>", status_code=500)


@router.get("/delete_all", response_class=HTMLResponse)
async def delete_all(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        count = notification_service.delete_all_notifications(db, user_id)

        return render_student_template(
            "notifications/delete_all_done.html",
            request,
            {
                "count": count,
                "page_title": "🧹 Đã xóa tất cả thông báo",
            },
        )

    except Exception:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi khi xóa tất cả.</h4>", status_code=500)


# ======================================================
# SETTINGS
# ======================================================
@router.get("/settings", response_class=HTMLResponse)
async def notification_settings(
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        settings = notification_service.get_user_notification_settings(db, user_id)

        return render_student_template(
            "notifications/settings.html",
            request,
            {
                "settings": settings,
                "message": None,
                "page_title": "⚙️ Cài đặt thông báo",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi tải cài đặt.</h4>", status_code=500)


@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    db: Session = Depends(get_db),
):
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

        notification_service.update_user_notification_settings(
            db,
            user_id,
            new_settings,
        )

        return render_student_template(
            "notifications/settings.html",
            request,
            {
                "settings": new_settings,
                "message": "✔ Đã lưu cài đặt.",
                "page_title": "⚙️ Cài đặt thông báo",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("<h4>❌ Lỗi lưu cài đặt.</h4>", status_code=500)