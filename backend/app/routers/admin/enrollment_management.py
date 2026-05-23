from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.classes import Class
from app.models.class_enrollment import ClassEnrollment
from app.models.user import User
from app.services.admin.enrollment_management_service import (
    add_enrollment,
    approve_enrollment,
    delete_enrollment as service_delete_enrollment,
    reject_enrollment,
    update_enrollment_status,
)

enrollment_router = APIRouter(
    prefix="/admin/enrollments",
    tags=["Admin - Quản lý ghi danh"],
)

CLASS_ENROLLMENT_STATUS_LABELS = {
    "applied": "Chờ duyệt",
    "approved": "Đã duyệt",
    "active": "Đang học",
    "rejected": "Đã từ chối",
    "removed": "Đã xóa khỏi lớp",
    "cancelled": "Đã hủy",
    "completed": "Đã hoàn thành",
}

ENROLLMENT_TYPE_LABELS = {
    "official": "Chính thức",
    "elective": "Tự chọn",
    "audit": "Dự thính",
    "temporary": "Tạm thời",
}


def vi_enrollment_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return CLASS_ENROLLMENT_STATUS_LABELS.get(key, "Không xác định")


def vi_enrollment_type(enrollment_type: str | None) -> str:
    key = (enrollment_type or "").strip().lower()
    return ENROLLMENT_TYPE_LABELS.get(key, "Khác")


def get_user_display_name(user) -> str:
    if not user:
        return "Không rõ"
    profile = getattr(user, "profile", None) or getattr(user, "user_profile", None)
    full_name = getattr(profile, "full_name", None) or getattr(user, "full_name", None)
    username = getattr(user, "username", None)
    email = getattr(user, "email", None)
    return full_name or username or email or "Không rõ"


def get_student_code(user) -> str:
    if not user:
        return ""
    student_profile = getattr(user, "student_profile", None) or getattr(user, "student_profiles", None)
    mssv = getattr(student_profile, "mssv", None) or getattr(user, "mssv", None)
    return mssv or ""


def render_template(
    request: Request,
    template_name: str,
    context: dict | None = None,
    status_code: int = 200,
):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "now": datetime.now(),
        "active_page": "enrollments",
        "vi_enrollment_status": vi_enrollment_status,
        "vi_enrollment_type": vi_enrollment_type,
        "get_user_display_name": get_user_display_name,
        "get_student_code": get_student_code,
        "status_labels": CLASS_ENROLLMENT_STATUS_LABELS,
        "type_labels": ENROLLMENT_TYPE_LABELS,
    }
    if context:
        base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


def _get_students(db: Session):
    sql = text(
        """
        SELECT u.id
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE r.role_code = 'student'
          AND u.deleted_at IS NULL
        ORDER BY u.username ASC
        """
    )
    ids = [row[0] for row in db.execute(sql).all()]
    return db.query(User).filter(User.id.in_(ids)).all() if ids else []


@enrollment_router.get("/", include_in_schema=False)
def redirect_enrollments_root():
    return RedirectResponse("/admin/enrollments/manage", status_code=303)


@enrollment_router.get("/manage", response_class=HTMLResponse)
def manage_enrollments(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    enrollments = (
        db.query(ClassEnrollment)
        .options(joinedload(ClassEnrollment.student), joinedload(ClassEnrollment.clazz))
        .order_by(ClassEnrollment.applied_at.desc())
        .all()
    )
    return render_template(
        request,
        "enrollments/manage.html",
        {"enrollments": enrollments, "admin": admin, "page_title": "Quản lý ghi danh lớp học"},
    )


@enrollment_router.get("/create", response_class=HTMLResponse)
def create_form(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    students = _get_students(db)
    classes = db.query(Class).order_by(Class.class_name.asc()).all()
    return render_template(
        request,
        "enrollments/create.html",
        {"students": students, "classes": classes, "admin": admin, "form_data": {}, "page_title": "Thêm ghi danh lớp học"},
    )


@enrollment_router.post("/create")
def add_enrollment_route(
    user_id: str = Form(...),
    class_id: str = Form(...),
    enrollment_type: str = Form("official"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    try:
        add_enrollment(db=db, user_id=user_id, class_id=class_id, enrollment_type=enrollment_type, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi ghi danh: {str(e)}") from e


@enrollment_router.get("/update/{enrollment_id}", response_class=HTMLResponse)
def update_form(
    request: Request,
    enrollment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    enrollment = (
        db.query(ClassEnrollment)
        .options(joinedload(ClassEnrollment.student), joinedload(ClassEnrollment.clazz))
        .filter(ClassEnrollment.id == enrollment_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu ghi danh.")
    return render_template(
        request,
        "enrollments/update.html",
        {"enrollment": enrollment, "admin": admin, "student_name": get_user_display_name(enrollment.student), "page_title": "Cập nhật ghi danh lớp học"},
    )


@enrollment_router.post("/update/{enrollment_id}")
def update_status(
    enrollment_id: str,
    new_status: str = Form(...),
    approved_by: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    try:
        update_enrollment_status(db=db, enrollment_id=enrollment_id, new_status=new_status, approved_by=approved_by or admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật trạng thái: {str(e)}") from e


@enrollment_router.post("/approve/{enrollment_id}")
def approve_route(enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        approve_enrollment(db=db, enrollment_id=enrollment_id, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phê duyệt đơn ghi danh: {str(e)}") from e


@enrollment_router.post("/reject/{enrollment_id}")
def reject_route(enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        reject_enrollment(db=db, enrollment_id=enrollment_id, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi từ chối đơn ghi danh: {str(e)}") from e


@enrollment_router.get("/delete/{enrollment_id}", response_class=HTMLResponse)
def delete_form(
    request: Request,
    enrollment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    enrollment = (
        db.query(ClassEnrollment)
        .options(joinedload(ClassEnrollment.student), joinedload(ClassEnrollment.clazz))
        .filter(ClassEnrollment.id == enrollment_id)
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu ghi danh.")
    return render_template(
        request,
        "enrollments/delete.html",
        {"enrollment": enrollment, "admin": admin, "student_name": get_user_display_name(enrollment.student), "page_title": "Xóa ghi danh lớp học"},
    )


@enrollment_router.post("/delete/{enrollment_id}")
def delete_route(enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        service_delete_enrollment(db=db, enrollment_id=enrollment_id, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa ghi danh: {str(e)}") from e
