from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.database.connection import get_db
from app.dependencies import get_current_user_id
from app.services.teacher import module_service, course_service

# ==============================
# 🧭 Cấu hình Template
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/modules"
)

# ==============================
# 🚀 Khởi tạo Router
# ==============================
router = APIRouter(
    prefix="/teacher/modules",
    tags=["Teacher - Modules Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách module theo khóa học
# =========================================================
@router.get("/list/{course_id}", response_class=HTMLResponse)
def module_list(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Hiển thị danh sách module của khóa học."""
    course = course_service.get_course_owned(db, user_id, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc bạn không có quyền truy cập.")

    modules = module_service.list_modules_by_course(db, course_id)
    print(f"🧩 [Modules] {len(modules)} modules found for course {course.course_name}")

    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "course": course,
            "modules": modules or [],
            "now": datetime.now()
        }
    )

# =========================================================
# ➕ 2️⃣ Trang tạo module
# =========================================================
@router.get("/create/{course_id}", response_class=HTMLResponse)
def page_create(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Trang form tạo module mới."""
    course = course_service.get_course_owned(db, user_id, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền truy cập.")

    return templates.TemplateResponse(
        "create.html",
        {
            "request": request,
            "course": course,
            "now": datetime.now()
        }
    )

# =========================================================
# 💾 3️⃣ Xử lý tạo module
# =========================================================
@router.post("/create/{course_id}")
def create_module(
    course_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    module_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    learning_objectives: str = Form("")
):
    """Lưu module mới vào cơ sở dữ liệu."""
    result = module_service.create_module(
        db, user_id, course_id, module_number, title, description, learning_objectives
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)

# =========================================================
# ✏️ 4️⃣ Trang chỉnh sửa module
# =========================================================
@router.get("/edit/{module_id}", response_class=HTMLResponse)
def page_edit(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Hiển thị form chỉnh sửa module."""
    module, course = module_service.get_module_owned_with_course(db, user_id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền chỉnh sửa.")

    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "module": module,
            "course": course,
            "now": datetime.now()
        }
    )

# =========================================================
# 💾 5️⃣ Xử lý cập nhật module
# =========================================================
@router.post("/edit/{module_id}")
def edit_module(
    module_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    module_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    learning_objectives: str = Form("")
):
    """Cập nhật thông tin module."""
    course_id = module_service.update_module(
        db, user_id, module_id, module_number, title, description, learning_objectives
    )
    if not course_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc không có quyền cập nhật.")

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)

# =========================================================
# ❌ 6️⃣ Trang xác nhận xóa module
# =========================================================
@router.get("/delete/{module_id}", response_class=HTMLResponse)
def page_delete(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Trang xác nhận xóa module."""
    module, course = module_service.get_module_owned_with_course(db, user_id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền xóa.")

    return templates.TemplateResponse(
        "delete.html",
        {
            "request": request,
            "module": module,
            "course": course,
            "now": datetime.now()
        }
    )

# =========================================================
# 🗑️ 7️⃣ Xử lý xóa module
# =========================================================
@router.post("/delete/{module_id}")
def delete_module(
    module_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Xóa module khỏi cơ sở dữ liệu."""
    course_id = module_service.delete_module(db, user_id, module_id)
    if not course_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền xóa.")

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)
