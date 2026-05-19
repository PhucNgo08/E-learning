from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.classes import Class
from app.models.enrollment import ClassEnrollment
from app.models.user import User
from app.services.admin.enrollment_management_service import (
    add_enrollment,
    approve_enrollment,
    delete_enrollment as service_delete_enrollment,
    reject_enrollment,
    update_enrollment_status,
)


enrollment_router = APIRouter(prefix="/admin/enrollments", tags=["Admin - Enrollment Management"])


def _get_students(db: Session):
    sql = text(
        """
        SELECT u.id
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE r.role_code = 'student' AND COALESCE(u.deleted_at, NULL) IS NULL
        ORDER BY u.username
        """
    )
    ids = [row[0] for row in db.execute(sql).all()]
    return db.query(User).filter(User.id.in_(ids)).all() if ids else []


@enrollment_router.get("/manage", response_class=HTMLResponse)
def manage_enrollments(request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    tpl = get_template_by_path(request.url.path)
    enrollments = (
        db.query(ClassEnrollment)
        .options(joinedload(ClassEnrollment.student), joinedload(ClassEnrollment.clazz))
        .order_by(ClassEnrollment.applied_at.desc())
        .all()
    )
    return tpl.TemplateResponse("enrollments/manage.html", {"request": request, "enrollments": enrollments, "admin": admin})


@enrollment_router.get("/create", response_class=HTMLResponse)
def create_form(request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    tpl = get_template_by_path(request.url.path)
    students = _get_students(db)
    classes = db.query(Class).order_by(Class.class_name.asc()).all()
    return tpl.TemplateResponse("enrollments/create.html", {"request": request, "students": students, "classes": classes, "admin": admin})


@enrollment_router.post("/create")
def add_enrollment_route(user_id: str = Form(...), class_id: str = Form(...), enrollment_type: str = Form("official"), db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    del admin
    try:
        add_enrollment(db=db, user_id=user_id, class_id=class_id, enrollment_type=enrollment_type, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Lỗi ghi danh: {str(e)}") from e


@enrollment_router.post("/update/{enrollment_id}")
def update_status(enrollment_id: str, new_status: str = Form(...), approved_by: str = Form(None), db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        update_enrollment_status(db=db, enrollment_id=enrollment_id, new_status=new_status, approved_by=approved_by or admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Lỗi cập nhật trạng thái: {str(e)}") from e


@enrollment_router.post("/approve/{enrollment_id}")
def approve_route(enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        approve_enrollment(db=db, enrollment_id=enrollment_id, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Lỗi phê duyệt đơn ghi danh: {str(e)}") from e


@enrollment_router.post("/reject/{enrollment_id}")
def reject_route(enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    try:
        reject_enrollment(db=db, enrollment_id=enrollment_id, approved_by=admin.id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Lỗi từ chối đơn ghi danh: {str(e)}") from e


@enrollment_router.get("/delete/{enrollment_id}", response_class=HTMLResponse)
def delete_form(request: Request, enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    tpl = get_template_by_path(request.url.path)
    enrollment = db.query(ClassEnrollment).options(joinedload(ClassEnrollment.student), joinedload(ClassEnrollment.clazz)).filter(ClassEnrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(404, "Không tìm thấy dữ liệu ghi danh.")
    return tpl.TemplateResponse("enrollments/delete.html", {"request": request, "enrollment": enrollment, "admin": admin})


@enrollment_router.post("/delete/{enrollment_id}")
def delete_route(enrollment_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    del admin
    try:
        service_delete_enrollment(db=db, enrollment_id=enrollment_id)
        return RedirectResponse("/admin/enrollments/manage", status_code=303)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"Lỗi xoá ghi danh: {str(e)}") from e
