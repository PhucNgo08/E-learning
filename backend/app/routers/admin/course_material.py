from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import course_material_service

# ✅ Dùng cấu hình template chung
from app.config.template_config import get_template_by_path

# ==========================================================
# 🚀 Router (Admin - Course Materials)
# ==========================================================
router = APIRouter(
    prefix="/admin/course-material",
    tags=["Admin - Course Materials"]
)

# ==========================================================
# 📄 1️⃣ Danh sách tài liệu
# ==========================================================
@router.get("/list", response_class=HTMLResponse)
def list_materials(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    materials = course_material_service.get_all(db)
    total = len(materials)
    return tpl.TemplateResponse(
        "course_material/list.html",
        {
            "request": request,
            "materials": materials,
            "total": total,
            "page_title": "📚 Quản lý tài liệu khóa học",
            "active_page": "course_material",
        },
    )

# ==========================================================
# ➕ 2️⃣ Tạo mới
# ==========================================================
@router.get("/create", response_class=HTMLResponse)
def create_material_form(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    courses = course_material_service.get_all_courses(db)
    return tpl.TemplateResponse(
        "course_material/create.html",
        {
            "request": request,
            "courses": courses,
            "page_title": "➕ Thêm tài liệu mới",
            "active_page": "course_material",
        },
    )


@router.post("/create")
async def create_material(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        # ✅ Lấy ID người tạo (admin đang đăng nhập)
        user_id = request.session.get("user_id") or "system"
        await course_material_service.create_material(
            db=db,
            title=title,
            description=description,
            course_id=course_id,
            file=file,
            created_by=user_id,
        )
        return RedirectResponse(url="/admin/course-material/list", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi khi tạo tài liệu: {e}")

# ==========================================================
# ✏️ 3️⃣ Chỉnh sửa
# ==========================================================
@router.get("/edit/{material_id}", response_class=HTMLResponse)
def edit_form(material_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    material = course_material_service.get_by_id(db, material_id)
    courses = course_material_service.get_all_courses(db)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return tpl.TemplateResponse(
        "course_material/edit.html",
        {
            "request": request,
            "material": material,
            "courses": courses,
            "page_title": "✏️ Chỉnh sửa tài liệu",
            "active_page": "course_material",
        },
    )


@router.post("/edit/{material_id}")
async def update_material(
    material_id: str,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    await course_material_service.update_material(db, material_id, title, description, file)
    return RedirectResponse(url="/admin/course-material/list", status_code=303)

# ==========================================================
# 🗑️ 4️⃣ Xóa tài liệu
# ==========================================================
@router.get("/delete/{material_id}", response_class=HTMLResponse)
def confirm_delete(material_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    return tpl.TemplateResponse(
        "course_material/delete.html",
        {
            "request": request,
            "material": material,
            "page_title": "🗑️ Xóa tài liệu",
            "active_page": "course_material",
        },
    )


@router.post("/delete/{material_id}")
def delete_material(material_id: str, db: Session = Depends(get_db)):
    course_material_service.delete_material(db, material_id)
    return RedirectResponse(url="/admin/course-material/list", status_code=303)
