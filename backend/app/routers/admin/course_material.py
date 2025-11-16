from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime

from app.config.paths import UPLOAD_MATERIALS
from app.database.connection import get_db
from app.services.admin import course_material_service
from app.models.course import Course
from app.config.template_config import get_template_by_path


router = APIRouter(
    prefix="/admin/course-material",
    tags=["Admin - Course Materials"]
)

# ==========================================================
# 📄 1) Danh sách tài liệu
# ==========================================================
@router.get("/list", response_class=HTMLResponse)
def list_materials(request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403, "Bạn không có quyền truy cập")

    tpl = get_template_by_path(request.url.path)
    materials = course_material_service.get_all(db)

    return tpl.TemplateResponse(
        "course_material/list.html",
        {
            "request": request,
            "materials": materials,
            "total": len(materials),
            "now": datetime.utcnow(),
            "page_title": "📚 Quản lý Tài liệu khóa học",
            "active_page": "course_material",
        },
    )


# ==========================================================
# ➕ 2) Form tạo mới
# ==========================================================
@router.get("/create", response_class=HTMLResponse)
def create_material_form(request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403, "Bạn không có quyền truy cập")

    tpl = get_template_by_path(request.url.path)
    courses = course_material_service.get_all_courses(db)

    return tpl.TemplateResponse(
        "course_material/create.html",
        {
            "request": request,
            "courses": courses,
            "error": None,
            "page_title": "➕ Thêm tài liệu mới",
            "active_page": "course_material",
        },
    )


# ==========================================================
# 💾 3) Tạo tài liệu (MULTIPLE UPLOAD)
# ==========================================================
@router.post("/create")
async def create_material(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    try:
        if request.session.get("role") != "admin":
            raise HTTPException(403, "Bạn không có quyền truy cập")

        if not files:
            raise HTTPException(400, "Bạn phải chọn ít nhất 1 file!")

        # Kiểm tra khóa học tồn tại
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(400, "Khóa học không tồn tại!")

        # ====================================================
        # 🔥 FIX QUAN TRỌNG: kiểm tra user_id có tồn tại trong DB
        # ====================================================
        from app.models.user import User

        user_id = request.session.get("user_id")
        if not user_id:
            request.session.clear()
            raise HTTPException(403, "Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại!")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            request.session.clear()
            raise HTTPException(403, "Tài khoản không tồn tại trong hệ thống. Vui lòng login lại!")
        # ====================================================

        await course_material_service.create_material(
            db=db,
            title=title,
            description=description,
            course_id=course_id,
            files=files,
            created_by=user_id,
        )

        return RedirectResponse(url="/admin/course-material/list", status_code=303)

    except Exception as e:
        tpl = get_template_by_path(request.url.path)
        courses = course_material_service.get_all_courses(db)

        return tpl.TemplateResponse(
            "course_material/create.html",
            {
                "request": request,
                "courses": courses,
                "error": str(e),
                "page_title": "➕ Thêm tài liệu mới",
                "active_page": "course_material",
            },
            status_code=400
        )


# ==========================================================
# 📘 4) Chi tiết + versions
# ==========================================================
@router.get("/detail/{material_id}", response_class=HTMLResponse)
def detail_material(material_id: str, request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403)

    tpl = get_template_by_path(request.url.path)
    material = course_material_service.get_by_id(db, material_id)

    if not material:
        raise HTTPException(404, "Không tìm thấy tài liệu.")

    versions = course_material_service.get_versions(db, material_id)

    return tpl.TemplateResponse(
        "course_material/detail.html",
        {
            "request": request,
            "material": material,
            "versions": versions,
            "now": datetime.utcnow(),
            "page_title": "📄 Chi tiết tài liệu",
            "active_page": "course_material",
        },
    )


# ==========================================================
# 📥 4.1 Download bản mới nhất
# ==========================================================
@router.get("/download/{material_id}")
def download_latest(material_id: str, request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403)

    material, file_path = course_material_service.get_download_latest(db, material_id)

    if not file_path.exists():
        raise HTTPException(404, "File không tồn tại trên server")

    course_material_service.increase_download_count(db, material)

    return FileResponse(
        path=file_path,
        filename=material.file_name,
        media_type=material.mime_type or "application/octet-stream",
    )


# ==========================================================
# 📥 4.2 Download theo phiên bản
# ==========================================================
@router.get("/download/{material_id}/version/{version}")
def download_version(material_id: str, version: str, request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403)

    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(404, "Không tìm thấy tài liệu.")

    for v in material.versions:
        if v.version == version:
            file_path = UPLOAD_MATERIALS / v.file_name

            if not file_path.exists():
                raise HTTPException(404, "File phiên bản này không tồn tại.")

            course_material_service.increase_download_count(db, material)

            return FileResponse(
                path=file_path,
                filename=v.file_name,
                media_type=v.mime_type or "application/octet-stream",
            )

    raise HTTPException(404, "Không tìm thấy phiên bản yêu cầu.")


# ==========================================================
# ✏️ 5) Form edit
# ==========================================================
@router.get("/edit/{material_id}", response_class=HTMLResponse)
def edit_form(material_id: str, request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403)

    tpl = get_template_by_path(request.url.path)
    material = course_material_service.get_by_id(db, material_id)
    courses = course_material_service.get_all_courses(db)

    if not material:
        raise HTTPException(404, "Không tìm thấy tài liệu.")

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


# ==========================================================
# 🔧 6) Update version mới
# ==========================================================
@router.post("/edit/{material_id}")
async def update_material(
    material_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    try:
        if request.session.get("role") != "admin":
            raise HTTPException(403)

        await course_material_service.update_material(
            db, material_id, title, description, file
        )

        return RedirectResponse("/admin/course-material/list", status_code=303)

    except Exception as e:
        raise HTTPException(400, f"Lỗi cập nhật tài liệu: {e}")


# ==========================================================
# 🗑️ 7) Xóa
# ==========================================================
@router.get("/delete/{material_id}", response_class=HTMLResponse)
def delete_confirm(material_id: str, request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403)

    tpl = get_template_by_path(request.url.path)
    material = course_material_service.get_by_id(db, material_id)

    if not material:
        raise HTTPException(404, "Không tìm thấy tài liệu.")

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
def delete_material(material_id: str, request: Request, db: Session = Depends(get_db)):

    if request.session.get("role") != "admin":
        raise HTTPException(403)

    course_material_service.delete_material(db, material_id)
    return RedirectResponse("/admin/course-material/list", status_code=303)
