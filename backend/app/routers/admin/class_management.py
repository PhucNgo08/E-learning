# ============================================================
# 🏫 class_management.py — Quản lý Lớp học (Admin)
# ============================================================
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

# ==============================
# 📦 Import DB & Models
# ==============================
from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.models.user import User
from app.services.admin.class_management_service import (
    create_class,
    get_all_classes,
    update_class,
    delete_class,
    get_class_by_id
)

# ✅ Import cấu hình template chung
from app.config.template_config import get_template_by_path

# ============================================================
# ⚙️ Cấu hình Router
# ============================================================
class_router = APIRouter(
    prefix="/admin/Class",
    tags=["Admin - Class Management"]
)

# ============================================================
# 📋 1️⃣ Danh sách lớp học
# ============================================================
@class_router.get("/manage", response_class=HTMLResponse)
def manage_classes(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách lớp học."""
    try:
        tpl = get_template_by_path(request.url.path)
        classes = get_all_classes(db)
        return tpl.TemplateResponse(
            "Class/manage.html",
            {"request": request, "classes": classes}
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải danh sách lớp: {str(e)}")

# ============================================================
# ➕ 2️⃣ Form thêm lớp học
# ============================================================
@class_router.get("/create", response_class=HTMLResponse)
def create_class_form(request: Request, db: Session = Depends(get_db)):
    """Hiển thị form tạo lớp học."""
    tpl = get_template_by_path(request.url.path)
    majors = db.query(Major).all()
    academic_years = db.query(AcademicYear).all()
    teachers = db.query(User).filter(User.role == "teacher").all()
    return tpl.TemplateResponse(
        "Class/create.html",
        {
            "request": request,
            "majors": majors,
            "academic_years": academic_years,
            "teachers": teachers
        }
    )

# ============================================================
# 💾 3️⃣ Xử lý thêm lớp học
# ============================================================
@class_router.post("/create")
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
    """Xử lý thêm mới lớp học."""
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
        print(f"✅ [Tạo lớp học] {class_code} - {class_name}")
        return RedirectResponse(url="/admin/Class/manage", status_code=303)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm lớp học: {str(e)}")

# ============================================================
# ✏️ 4️⃣ Form chỉnh sửa lớp học
# ============================================================
@class_router.get("/edit/{class_id}", response_class=HTMLResponse)
def edit_class_form(request: Request, class_id: str, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa lớp học."""
    tpl = get_template_by_path(request.url.path)
    clazz = get_class_by_id(class_id, db)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    majors = db.query(Major).all()
    academic_years = db.query(AcademicYear).all()
    teachers = db.query(User).filter(User.role == "teacher").all()
    return tpl.TemplateResponse(
        "Class/edit.html",
        {
            "request": request,
            "cls": clazz,
            "majors": majors,
            "academic_years": academic_years,
            "teachers": teachers
        }
    )

# ============================================================
# 🔄 5️⃣ Xử lý cập nhật lớp học
# ============================================================
@class_router.post("/edit/{class_id}")
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
    """Xử lý cập nhật lớp học."""
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
        print(f"✏️ [Cập nhật lớp học] {class_name}")
        return RedirectResponse(url="/admin/Class/manage", status_code=303)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật lớp học: {str(e)}")

# ============================================================
# ❌ 6️⃣ Xác nhận xóa lớp học
# ============================================================
@class_router.get("/delete/{class_id}", response_class=HTMLResponse)
def delete_class_form(request: Request, class_id: str, db: Session = Depends(get_db)):
    """Hiển thị trang xác nhận xóa lớp học."""
    tpl = get_template_by_path(request.url.path)
    clazz = get_class_by_id(class_id, db)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    return tpl.TemplateResponse(
        "Class/delete.html",
        {"request": request, "cls": clazz}
    )

# ============================================================
# 🗑️ 7️⃣ Xử lý xóa lớp học
# ============================================================
@class_router.post("/delete/{class_id}")
def remove_class(class_id: str, db: Session = Depends(get_db)):
    """Xử lý xóa lớp học."""
    try:
        delete_class(class_id, db)
        print(f"🗑️ [Xóa lớp học] ID: {class_id}")
        return RedirectResponse(url="/admin/Class/manage", status_code=303)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa lớp học: {str(e)}")
