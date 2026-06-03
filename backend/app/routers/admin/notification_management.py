"""
==========================================================
🔔 ROUTER: Admin - Notification Management
Quản lý và gửi thông báo hệ thống
- Gửi từng người nhận
- Gửi theo khóa học
- Gửi tất cả người dùng
==========================================================
"""
from datetime import datetime
import traceback
import uuid

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin

from app.models.notification import Notification
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment


router = APIRouter(
    prefix="/admin/notification",
    tags=["Admin - Notification Management"],
)

ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    tpl = get_template_by_path(request.url.path)

    base_context = {
        "request": request,
        "page_title": "🔔 Quản lý thông báo",
        "active_page": "notification",
    }
    base_context.update(context)

    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def get_user_map(db: Session) -> dict[str, str]:
    rows = db.query(UserProfile.user_id, UserProfile.full_name).all()
    return {row.user_id: row.full_name for row in rows}


def get_user_choices(db: Session) -> list[dict]:
    rows = (
        db.query(
            User.id.label("id"),
            User.username.label("username"),
            UserProfile.full_name.label("full_name"),
        )
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .order_by(UserProfile.full_name.asc(), User.username.asc())
        .all()
    )

    users: list[dict] = []
    for row in rows:
        display_name = (row.full_name or row.username or "").strip()
        users.append(
            {
                "id": row.id,
                "name": display_name,
                "username": row.username,
            }
        )

    return users


def get_selected_users(db: Session, user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []

    rows = (
        db.query(
            User.id.label("id"),
            User.username.label("username"),
            UserProfile.full_name.label("full_name"),
        )
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(User.id.in_(user_ids))
        .all()
    )

    selected_users: list[dict] = []
    for row in rows:
        selected_users.append(
            {
                "id": row.id,
                "name": (row.full_name or row.username or "").strip(),
                "username": row.username,
            }
        )

    return selected_users


def get_course_choices(db: Session) -> list[dict]:
    rows = (
        db.query(
            Course.id.label("id"),
            Course.course_code.label("course_code"),
            Course.course_name.label("course_name"),
        )
        .filter(Course.deleted_at.is_(None))
        .order_by(Course.course_code.asc(), Course.course_name.asc())
        .all()
    )

    courses: list[dict] = []
    for row in rows:
        course_code = row.course_code or ""
        course_name = row.course_name or ""
        courses.append(
            {
                "id": row.id,
                "name": f"{course_code} - {course_name}".strip(" -"),
            }
        )

    return courses


def get_course_student_ids(db: Session, course_id: str) -> list[str]:
    rows = (
        db.query(CourseEnrollment.user_id)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .all()
    )

    return list(dict.fromkeys([row.user_id for row in rows if row.user_id]))


def create_notifications_for_users(
    db: Session,
    user_ids: list[str],
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> int:
    unique_user_ids = list(dict.fromkeys([uid for uid in user_ids if uid]))

    for uid in unique_user_ids:
        db.add(
            Notification(
                id=str(uuid.uuid4()),
                user_id=uid,
                title=title,
                message=message,
                notification_type=notification_type,
                link_url=link_url,
                is_read=False,
                read_at=None,
                created_at=datetime.utcnow(),
            )
        )

    return len(unique_user_ids)


@router.get("/list", response_class=HTMLResponse)
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        notifications = (
            db.query(Notification)
            .order_by(Notification.created_at.desc())
            .all()
        )
        user_map = get_user_map(db)

        return render_template(
            request,
            "notification/list.html",
            {
                "notifications": notifications,
                "user_map": user_map,
                "total": len(notifications),
                "page_title": "🔔 Quản lý Thông báo",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse(
            f"<pre style='color:red'>{traceback.format_exc()}</pre>",
            status_code=500,
        )


@router.get("/create", response_class=HTMLResponse)
def create_notification_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    users = get_user_choices(db)
    courses = get_course_choices(db)

    return render_template(
        request,
        "notification/create.html",
        {
            "users": users,
            "courses": courses,
            "selected_users": [],
            "form_data": {
                "title": "",
                "message": "",
                "target_mode": "users",
                "course_id": "",
                "user_ids": "",
            },
            "error_message": None,
            "page_title": "📨 Gửi thông báo mới",
        },
    )


@router.post("/create", response_class=HTMLResponse)
def create_notification_action(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
    title: str = Form(...),
    message: str = Form(...),
    target_mode: str = Form("users"),
    course_id: str = Form(""),
    user_ids: str = Form(""),
):
    users = get_user_choices(db)
    courses = get_course_choices(db)

    title = (title or "").strip()
    message = (message or "").strip()
    target_mode = (target_mode or "users").strip()
    course_id = (course_id or "").strip()
    raw_user_ids = (user_ids or "").strip()

    selected_user_ids = list(
        dict.fromkeys([uid.strip() for uid in raw_user_ids.split(",") if uid.strip()])
    )
    selected_users = get_selected_users(db, selected_user_ids)

    form_data = {
        "title": title,
        "message": message,
        "target_mode": target_mode,
        "course_id": course_id,
        "user_ids": ",".join(selected_user_ids),
    }

    def render_error(error_message: str, status_code: int = 400):
        return render_template(
            request,
            "notification/create.html",
            {
                "users": users,
                "courses": courses,
                "selected_users": selected_users,
                "form_data": form_data,
                "error_message": error_message,
                "page_title": "📨 Gửi thông báo mới",
            },
            status_code=status_code,
        )

    if not title:
        return render_error("Tiêu đề không được để trống.")

    if not message:
        return render_error("Nội dung không được để trống.")

    try:
        target_user_ids: list[str] = []

        if target_mode == "all":
            target_user_ids = [row.id for row in db.query(User.id).all()]

            if not target_user_ids:
                return render_error("Không có người dùng nào trong hệ thống.")

        elif target_mode == "course":
            if not course_id:
                return render_error("Vui lòng chọn khóa học cần gửi thông báo.")

            course = (
                db.query(Course)
                .filter(
                    Course.id == course_id,
                    Course.deleted_at.is_(None),
                )
                .first()
            )

            if not course:
                return render_error("Khóa học không tồn tại hoặc đã bị xóa.")

            target_user_ids = get_course_student_ids(db, course_id)

            if not target_user_ids:
                return render_error("Khóa học này chưa có sinh viên đang học.")

        elif target_mode == "users":
            if not selected_user_ids:
                return render_error("Vui lòng chọn ít nhất một người nhận.")

            valid_user_ids = {
                row.id
                for row in db.query(User.id).filter(User.id.in_(selected_user_ids)).all()
            }

            target_user_ids = list(valid_user_ids)

            if not target_user_ids:
                return render_error("Danh sách người nhận không hợp lệ.")

        else:
            return render_error("Kiểu gửi thông báo không hợp lệ.")

        sent_count = create_notifications_for_users(
            db=db,
            user_ids=target_user_ids,
            title=title,
            message=message,
            notification_type="system",
            link_url=None,
        )

        if sent_count <= 0:
            return render_error("Không tìm thấy người nhận phù hợp.")

        db.commit()
        return RedirectResponse("/admin/notification/list", status_code=303)

    except Exception:
        db.rollback()
        traceback.print_exc()
        return render_error(
            "Có lỗi xảy ra khi tạo thông báo. Vui lòng thử lại.",
            status_code=500,
        )


@router.get("/delete/{notification_id}", response_class=HTMLResponse)
def confirm_delete_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")

    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == notification.user_id)
        .first()
    )

    user_name = profile.full_name if profile else "Không rõ"

    return render_template(
        request,
        "notification/delete.html",
        {
            "notification": notification,
            "user_name": user_name,
            "page_title": "🗑️ Xóa thông báo",
        },
    )


@router.post("/delete/{notification_id}")
def delete_notification_action(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )

        if not notification:
            raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")

        db.delete(notification)
        db.commit()

        return RedirectResponse("/admin/notification/list", status_code=303)

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Có lỗi xảy ra khi xóa thông báo.",
        )