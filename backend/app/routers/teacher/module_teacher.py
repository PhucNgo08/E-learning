from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

# ==============================
# 📦 Import nội bộ
# ==============================
from app.services import course_service
from app.services.teacher import module_service
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path


# ==============================
# 🚀 Khởi tạo Router
# ==============================
router = APIRouter(
    prefix="/teacher/modules",
    tags=["Teacher - Modules Management"]
)


# =========================================================
# 🧭 0️⃣ Redirect gốc → /list-all
# =========================================================
@router.get("/", include_in_schema=False)
def redirect_root():
    """Truy cập /teacher/modules → /teacher/modules/list-all"""
    return RedirectResponse("/teacher/modules/list-all", status_code=303)


# =========================================================
# 📋 1️⃣ Danh sách module theo khóa học
# =========================================================
@router.get("/list/{course_id}", response_class=HTMLResponse)
def module_list(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách module của một khóa học."""
    course = course_service.get_course_owned(db, current_teacher.id, course_id, role="teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc bạn không có quyền truy cập.")

    modules = module_service.list_modules_by_course(db, course_id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "modules/list.html",
        {
            "request": request,
            "teacher": current_teacher,
            "course": course,
            "modules": modules or [],
            "page_title": f"📚 Danh sách module - {course.course_name}",
        },
    )


# =========================================================
# 📚 2️⃣ Danh sách tất cả module của giáo viên
# =========================================================
@router.get("/list-all", response_class=HTMLResponse)
def list_all_modules(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Liệt kê toàn bộ module thuộc các khóa học mà giáo viên sở hữu."""
    modules = module_service.list_all_modules_by_teacher(db, current_teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "modules/list_all.html",
        {
            "request": request,
            "teacher": current_teacher,
            "modules": modules,
            "page_title": "📘 Tất cả module của bạn",
        },
    )


# =========================================================
# ➕ 3️⃣ Trang tạo module
# =========================================================
@router.get("/create/{course_id}", response_class=HTMLResponse)
def page_create(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form tạo module mới."""
    course = course_service.get_course_owned(db, current_teacher.id, course_id, role="teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc bạn không có quyền truy cập.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "modules/create.html",
        {
            "request": request,
            "teacher": current_teacher,
            "course": course,
            "page_title": f"➕ Thêm module cho {course.course_name}",
        },
    )


# =========================================================
# 💾 4️⃣ Xử lý tạo module
# =========================================================
@router.post("/create/{course_id}")
def create_module(
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    module_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    learning_objectives: str = Form(""),
):
    """Xử lý tạo module mới."""
    result = module_service.create_module(
        db, current_teacher.id, course_id, module_number, title, description, learning_objectives
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)


# =========================================================
# ✏️ 5️⃣ Trang chỉnh sửa module
# =========================================================
@router.get("/edit/{module_id}", response_class=HTMLResponse)
def page_edit(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form chỉnh sửa module."""
    module, course = module_service.get_module_owned_with_course(db, current_teacher.id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền chỉnh sửa.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "modules/edit.html",
        {
            "request": request,
            "teacher": current_teacher,
            "module": module,
            "course": course,
            "page_title": f"✏️ Chỉnh sửa module: {module.title}",
        },
    )


# =========================================================
# 💾 6️⃣ Xử lý cập nhật module
# =========================================================
@router.post("/edit/{module_id}")
def edit_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    module_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    learning_objectives: str = Form(""),
):
    """Cập nhật thông tin module."""
    course_id = module_service.update_module(
        db, current_teacher.id, module_id, module_number, title, description, learning_objectives
    )
    if not course_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc không có quyền cập nhật.")

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)


# =========================================================
# ❌ 7️⃣ Trang xác nhận xóa module
# =========================================================
@router.get("/delete/{module_id}", response_class=HTMLResponse)
def page_delete(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Trang xác nhận xóa module."""
    module, course = module_service.get_module_owned_with_course(db, current_teacher.id, module_id)
    if not module or not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền xóa.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "modules/delete.html",
        {
            "request": request,
            "teacher": current_teacher,
            "module": module,
            "course": course,
            "page_title": f"🗑️ Xóa module: {module.title}",
        },
    )


# =========================================================
# 🗑️ 8️⃣ Xử lý xóa module
# =========================================================
@router.post("/delete/{module_id}")
def delete_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xóa module khỏi cơ sở dữ liệu."""
    course_id = module_service.delete_module(db, current_teacher.id, module_id)
    if not course_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc không có quyền xóa.")

    return RedirectResponse(f"/teacher/modules/list/{course_id}", status_code=303)


# =========================================================
# 📢 9️⃣ Đăng / Gỡ đăng module
# =========================================================
@router.get("/publish/{module_id}", response_class=RedirectResponse)
def publish_module(
    module_id: str,
    publish: bool = True,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Cập nhật trạng thái xuất bản module."""
    result = module_service.publish_module(db, current_teacher.id, module_id, publish)
    if not result:
        raise HTTPException(status_code=404, detail="Không thể cập nhật trạng thái module.")

    return RedirectResponse(f"/teacher/modules/list/{result.course_id}", status_code=303)
