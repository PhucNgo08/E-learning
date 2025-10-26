"""
==========================================================
🎓 ROUTER: Teacher - Materials
Quản lý upload, danh sách, sửa và xóa tài liệu khóa học của giáo viên
==========================================================
"""

from fastapi import (
    APIRouter, Request, Form, File, UploadFile, Depends, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime

# ✅ Import cấu hình hệ thống
from app.database.connection import get_db
from app.config.template_config import get_template_by_path

# ✅ Import dependencies & services
from app.dependencies.auth import get_current_teacher
from app.services.teacher import material_teacher_service as material_service


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/teacher/materials",
    tags=["Teacher - Materials"]
)


# ======================================================
# 🧭 0️⃣ Redirect gốc → /list
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    """Tự động chuyển /teacher/materials → /teacher/materials/list"""
    return RedirectResponse("/teacher/materials/list", status_code=303)


# ======================================================
# 📋 1️⃣ Danh sách tài liệu của giáo viên
# ======================================================
@router.get("/list", response_class=HTMLResponse)
async def list_materials(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách tài liệu mà giáo viên đã upload"""
    teacher = current_teacher
    materials = material_service.get_all(db, teacher.id)
    stats = material_service.get_statistics(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "materials/list.html",
        {
            "request": request,
            "teacher": teacher,
            "materials": materials,
            "stats": stats,
            "page_title": "📂 Danh sách tài liệu khóa học",
            "now": datetime.now(),
        },
    )


# ======================================================
# 📤 2️⃣ Trang upload tài liệu
# ======================================================
@router.get("/upload", response_class=HTMLResponse)
async def upload_form(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form upload tài liệu"""
    teacher = current_teacher
    courses = material_service.get_courses_by_teacher(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "materials/upload.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "page_title": "📤 Upload tài liệu khóa học",
            "now": datetime.now(),
        },
    )


# ======================================================
# 🚀 3️⃣ Upload tài liệu (POST)
# ======================================================
@router.post("/upload")
async def upload_material(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    course_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
):
    """Xử lý upload tài liệu"""
    teacher = current_teacher
    result = await material_service.create_material(
        db=db,
        title=title,
        description=description,
        course_id=course_id,
        file=file,
        created_by=teacher.id,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/materials/list", status_code=303)


# ======================================================
# ✏️ 4️⃣ Cập nhật tài liệu
# ======================================================
@router.post("/edit/{material_id}")
async def edit_material(
    material_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile | None = File(None),
):
    """Cập nhật thông tin tài liệu"""
    teacher = current_teacher
    result = await material_service.update_material(
        db, teacher.id, material_id, title, description, file
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/materials/list", status_code=303)


# ======================================================
# 🗑️ 5️⃣ Xóa tài liệu
# ======================================================
@router.post("/delete/{material_id}")
async def delete_material(
    material_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xóa tài liệu"""
    teacher = current_teacher
    result = material_service.delete_material(db, teacher.id, material_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/materials/list", status_code=303)
