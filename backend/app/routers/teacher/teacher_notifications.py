"""
==========================================================
🔔 ROUTER: Teacher - Notifications
Hiển thị danh sách, chi tiết, đánh dấu đọc và xóa thông báo của giáo viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path
from app.services.teacher import notification_service


router = APIRouter(
    prefix="/teacher/notifications",
    tags=["Teacher - Notifications"],
)


def build_notification_context(db: Session, teacher_id: str) -> dict:
    latest_notifications = notification_service.get_latest_notifications(
        db=db,
        user_id=teacher_id,
        limit=5,
    )

    unread_notification_count = notification_service.count_unread_notifications(
        db=db,
        user_id=teacher_id,
    )

    return {
        "latest_notifications": latest_notifications,
        "unread_notification_count": unread_notification_count,
    }


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

    return templates.TemplateResponse(
        template_name,
        base_context,
        status_code=status_code,
    )


@router.get("/api/summary")
def teacher_notification_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    latest_notifications = notification_service.get_latest_notifications(
        db=db,
        user_id=teacher.id,
        limit=5,
    )

    unread_count = notification_service.count_unread_notifications(
        db=db,
        user_id=teacher.id,
    )

    data = []
    for n in latest_notifications:
        data.append(
            {
                "id": n.id,
                "title": n.title or "Thông báo",
                "message": n.message or "",
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


@router.get("/", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    notifications = notification_service.get_notifications_by_user(
        db=db,
        user_id=teacher.id,
    )

    layout_context = build_notification_context(db, teacher.id)

    return render_template(
        request,
        "notifications/list.html",
        {
            "teacher": teacher,
            "notifications": notifications,
            "page_title": "🔔 Thông báo của tôi",
            **layout_context,
        },
    )


@router.get("/detail/{notification_id}", response_class=HTMLResponse)
def detail_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    notification = notification_service.get_notification_detail(
        db=db,
        notification_id=notification_id,
        user_id=teacher.id,
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")

    notification_service.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=teacher.id,
    )

    notification = notification_service.get_notification_detail(
        db=db,
        notification_id=notification_id,
        user_id=teacher.id,
    ) or notification

    if notification.link_url:
        return RedirectResponse(url=notification.link_url, status_code=303)

    layout_context = build_notification_context(db, teacher.id)

    return render_template(
        request,
        "notifications/detail.html",
        {
            "teacher": teacher,
            "notification": notification,
            "page_title": f"📩 {notification.title}",
            **layout_context,
        },
    )


@router.post("/read/{notification_id}")
def mark_notification_as_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    notification = notification_service.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=teacher.id,
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")

    return RedirectResponse(
        url="/teacher/notifications/",
        status_code=303,
    )


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    notification_service.mark_all_as_read_by_user(
        db=db,
        user_id=teacher.id,
    )

    return RedirectResponse(
        url="/teacher/notifications/",
        status_code=303,
    )


@router.post("/delete/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    deleted = notification_service.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=teacher.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông báo để xóa.",
        )

    return RedirectResponse(
        url="/teacher/notifications/",
        status_code=303,
    )