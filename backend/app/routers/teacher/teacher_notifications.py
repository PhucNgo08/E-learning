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


router = APIRouter(
    prefix="/teacher/notifications",
    tags=["Teacher - Notifications"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "active_page": "notifications",
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    notifications = notification_service.get_notifications_by_user(db, teacher.id)

    return render_template(
        request,
        "notifications/list.html",
        {
            "teacher": teacher,
            "notifications": notifications,
            "page_title": "🔔 Thông báo của tôi",
        },
    )


@router.get("/detail/{notification_id}", response_class=HTMLResponse)
def detail_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher

    notification = notification_service.get_notification_detail(db, notification_id, teacher.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")

    notification = notification_service.mark_as_read(db, notification_id, teacher.id) or notification

    if notification.link_url:
        return RedirectResponse(url=notification.link_url, status_code=303)

    return render_template(
        request,
        "notifications/detail.html",
        {
            "teacher": teacher,
            "notification": notification,
            "page_title": f"📩 {notification.title}",
        },
    )


@router.post("/delete/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    deleted = notification_service.delete_notification(db, notification_id, teacher.id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo để xóa")

    return RedirectResponse(url="/teacher/notifications", status_code=303)