"""
===========================================================
📘 ROUTER: Admin - Enrollment Management (Final v3.0)
Quản lý ghi danh học viên vào lớp (CRUD + Approve/Reject)
===========================================================
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.models.enrollment import Enrollment
from app.models.user import User
from app.models.classes import Class

from app.services.admin.enrollment_management_service import (
    add_enrollment,
    update_enrollment_status,
    delete_enrollment as service_delete_enrollment,
    approve_enrollment,
    reject_enrollment,
)

from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin


# =====================================================
# 🚦 Router
# =====================================================
enrollment_router = APIRouter(
    prefix="/admin/enrollments",
    tags=["Admin - Enrollment Management"]
)


# =====================================================
# 📋 1) Danh sách đơn ghi danh
# =====================================================
@enrollment_router.get("/manage", response_class=HTMLResponse)
def manage_enrollments(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    tpl = get_template_by_path(request.url.path)

    enrollments = (
        db.query(Enrollment)
        .order_by(Enrollment.applied_at.desc())
        .all()
    )

    return tpl.TemplateResponse(
        "enrollments/manage.html",
        {"request": request, "enrollments": enrollments}
    )


# =====================================================
# ➕ 2) Form tạo ghi danh
# =====================================================
@enrollment_router.get("/create", response_class=HTMLResponse)
def create_form(
    request: Request,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    tpl = get_template_by_path(request.url.path)

    students = db.query(User).filter(User.role == "student").all()
    classes = db.query(Class).all()

    return tpl.TemplateResponse(
        "enrollments/create.html",
        {"request": request, "students": students, "classes": classes}
    )


# =====================================================
# 💾 3) Xử lý tạo ghi danh
# =====================================================
@enrollment_router.post("/create")
def add_enrollment_route(
    user_id: str = Form(...),
    class_id: str = Form(...),
    enrollment_type: str = Form("official"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    try:
        add_enrollment(
            user_id=user_id,
            class_id=class_id,
            enrollment_type=enrollment_type,
            db=db
        )

        return RedirectResponse("/admin/enrollments/manage", status_code=303)

    except Exception as e:
        raise HTTPException(500, f"Lỗi ghi danh: {str(e)}")


# =====================================================
# ✏️ 4) Update trạng thái (chung)
# =====================================================
@enrollment_router.post("/update/{enrollment_id}")
def update_status(
    enrollment_id: str,
    new_status: str = Form(...),
    approved_by: str = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    try:
        update_enrollment_status(
            enrollment_id=enrollment_id,
            new_status=new_status,
            approved_by=approved_by,
            db=db
        )
        return RedirectResponse("/admin/enrollments/manage", status_code=303)

    except Exception as e:
        raise HTTPException(500, f"Lỗi cập nhật trạng thái: {str(e)}")


# =====================================================
# ✔ 5) APPROVE đơn ghi danh
# =====================================================
@enrollment_router.post("/approve/{enrollment_id}")
def approve_route(
    enrollment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    try:
        approve_enrollment(
            enrollment_id=enrollment_id,
            approved_by=admin.id,
            db=db
        )

        return RedirectResponse("/admin/enrollments/manage", status_code=303)

    except Exception as e:
        raise HTTPException(500, f"Lỗi phê duyệt đơn ghi danh: {str(e)}")


# =====================================================
# ❌ 6) REJECT đơn ghi danh
# =====================================================
@enrollment_router.post("/reject/{enrollment_id}")
def reject_route(
    enrollment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    try:
        reject_enrollment(
            enrollment_id=enrollment_id,
            approved_by=admin.id,
            db=db
        )

        return RedirectResponse("/admin/enrollments/manage", status_code=303)

    except Exception as e:
        raise HTTPException(500, f"Lỗi từ chối đơn ghi danh: {str(e)}")


# =====================================================
# ❌ 7) Form xác nhận xóa
# =====================================================
@enrollment_router.get("/delete/{enrollment_id}", response_class=HTMLResponse)
def delete_form(
    request: Request,
    enrollment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    tpl = get_template_by_path(request.url.path)

    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(404, "Không tìm thấy dữ liệu ghi danh.")

    return tpl.TemplateResponse(
        "enrollments/delete.html",
        {"request": request, "enrollment": enrollment}
    )


# =====================================================
# 🗑️ 8) Xử lý xóa ghi danh
# =====================================================
@enrollment_router.post("/delete/{enrollment_id}")
def delete_route(
    enrollment_id: str,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    try:
        service_delete_enrollment(enrollment_id, db)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)

    except Exception as e:
        raise HTTPException(500, f"Lỗi xoá ghi danh: {str(e)}")
