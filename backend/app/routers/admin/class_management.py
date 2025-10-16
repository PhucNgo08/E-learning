from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.models.user import User
from app.services.class_management_service import (
    create_class, get_all_classes, update_class, delete_class, get_class_by_id
)
from datetime import datetime

# ============================================================
# ⚙️ Cấu hình Router & Template
# ============================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/Class"
)

class_router = APIRouter(prefix="/admin", tags=["Admin - Class Management"])

# ============================================================
# 📋 Danh sách lớp học
# ============================================================
@class_router.get("/Class/manage", response_class=HTMLResponse)
def manage_classes(request: Request, db: Session = Depends(get_db)):
    classes = get_all_classes(db)
    return templates.TemplateResponse(
        "manage.html", {"request": request, "classes": classes}
    )

# ============================================================
# ➕ Form thêm lớp học
# ============================================================
@class_router.get("/Class/create", response_class=HTMLResponse)
def create_class_form(request: Request, db: Session = Depends(get_db)):
    majors = db.query(Major).all()
    academic_years = db.query(AcademicYear).all()
    teachers = db.query(User).filter(User.role == "teacher").all()
    return templates.TemplateResponse(
        "create.html",
        {
            "request": request,
            "majors": majors,
            "academic_years": academic_years,
            "teachers": teachers,
        },
    )

# ============================================================
# 💾 Xử lý thêm lớp học
# ============================================================
@class_router.post("/Class/create")
def add_class(
    class_code: str = Form(...),
    class_name: str = Form(...),
    class_type: str = Form("official"),
    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    homeroom_teacher_id: str = Form(None),
    max_students: int = Form(50),
    start_date: str = Form(None),
    end_date: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        create_class(
            class_code,
            class_name,
            class_type,
            academic_year_id,
            major_id,
            homeroom_teacher_id,
            max_students,
            start_dt,
            end_dt,
            db,
        )
        return RedirectResponse(url="/admin/Class/manage", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm lớp học: {str(e)}")

# ============================================================
# ✏️ Form chỉnh sửa lớp học
# ============================================================
@class_router.get("/Class/edit/{class_id}", response_class=HTMLResponse)
def edit_class_form(request: Request, class_id: str, db: Session = Depends(get_db)):
    clazz = get_class_by_id(class_id, db)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    majors = db.query(Major).all()
    academic_years = db.query(AcademicYear).all()
    teachers = db.query(User).filter(User.role == "teacher").all()
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "cls": clazz,
            "majors": majors,
            "academic_years": academic_years,
            "teachers": teachers,
        },
    )

# ============================================================
# 🔄 Xử lý cập nhật lớp học
# ============================================================
@class_router.post("/Class/edit/{class_id}")
def edit_class(
    class_id: str,
    class_name: str = Form(...),
    class_type: str = Form(...),
    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    homeroom_teacher_id: str = Form(None),
    max_students: int = Form(...),
    status: str = Form("active"),
    start_date: str = Form(None),
    end_date: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        update_class(
            class_id,
            class_name,
            class_type,
            max_students,
            status,
            db,
        )
        return RedirectResponse(url="/admin/Class/manage", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật lớp học: {str(e)}")

# ============================================================
# ❌ Xác nhận xóa lớp học
# ============================================================
@class_router.get("/Class/delete/{class_id}", response_class=HTMLResponse)
def delete_class_form(request: Request, class_id: str, db: Session = Depends(get_db)):
    clazz = get_class_by_id(class_id, db)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    return templates.TemplateResponse(
        "delete.html", {"request": request, "cls": clazz}
    )

# ============================================================
# 🗑️ Xử lý xóa lớp học
# ============================================================
@class_router.post("/Class/delete/{class_id}")
def remove_class(class_id: str, db: Session = Depends(get_db)):
    try:
        delete_class(class_id, db)
        return RedirectResponse(url="/admin/Class/manage", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa lớp học: {str(e)}")
