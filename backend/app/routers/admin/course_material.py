from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    UploadFile,
    File,
    HTTPException,
    Query,
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.config.paths import UPLOAD_MATERIALS
from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.models.course import Course
from app.models.user import User
from app.services.admin import course_material_service

router = APIRouter(
    prefix="/admin/course-material",
    tags=["Admin - Course Materials"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.utcnow().year,
        "active_page": "course_material",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def ensure_admin(request: Request):
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")


@router.get("/list", response_class=HTMLResponse)
def list_materials(
    request: Request,
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    ensure_admin(request)

    materials = course_material_service.get_all(db)

    return render_template(
        request,
        "course_material/list.html",
        {
            "materials": materials,
            "total": len(materials),
            "now": datetime.utcnow(),
            "success": success,
            "error": error,
            "page_title": "📚 Quản lý Tài liệu khóa học",
        },
    )


@router.get("/create", response_class=HTMLResponse)
def create_material_form(request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    courses = course_material_service.get_all_courses(db)

    return render_template(
        request,
        "course_material/create.html",
        {
            "courses": courses,
            "error": None,
            "form_data": {
                "title": "",
                "description": "",
                "course_id": "",
            },
            "page_title": "➕ Thêm tài liệu mới",
        },
    )


@router.post("/create", response_class=HTMLResponse)
async def create_material(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    ensure_admin(request)

    courses = course_material_service.get_all_courses(db)
    form_data = {
        "title": title,
        "description": description or "",
        "course_id": course_id,
    }

    try:
        if not files:
            raise ValueError("Bạn phải chọn ít nhất 1 file.")

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError("Khóa học không tồn tại.")

        user_id = request.session.get("user_id")
        if not user_id:
            request.session.clear()
            raise HTTPException(status_code=403, detail="Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            request.session.clear()
            raise HTTPException(status_code=403, detail="Tài khoản không tồn tại. Vui lòng đăng nhập lại.")

        await course_material_service.create_material(
            db=db,
            title=title,
            description=description,
            course_id=course_id,
            files=files,
            created_by=user_id,
        )

        message = quote("Tạo tài liệu thành công.")
        return RedirectResponse(url=f"/admin/course-material/list?success={message}", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        return render_template(
            request,
            "course_material/create.html",
            {
                "courses": courses,
                "error": str(e),
                "form_data": form_data,
                "page_title": "➕ Thêm tài liệu mới",
            },
            status_code=400,
        )


@router.get("/detail/{material_id}", response_class=HTMLResponse)
def detail_material(material_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    versions = course_material_service.get_versions(db, material_id)

    return render_template(
        request,
        "course_material/detail.html",
        {
            "material": material,
            "versions": versions,
            "now": datetime.utcnow(),
            "page_title": "📄 Chi tiết tài liệu",
        },
    )


@router.get("/download/{material_id}")
def download_latest(material_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    try:
        material, file_path = course_material_service.get_download_latest(db, material_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    course_material_service.increase_download_count(db, material)

    return FileResponse(
        path=file_path,
        filename=material.file_name,
        media_type=material.mime_type or "application/octet-stream",
    )


@router.get("/download/{material_id}/version/{version}")
def download_version(material_id: str, version: str, request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    versions = course_material_service.get_versions(db, material_id)
    for v in versions:
        if v.version == version:
            file_path = UPLOAD_MATERIALS / v.file_name

            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File phiên bản này không tồn tại.")

            course_material_service.increase_download_count(db, material)

            return FileResponse(
                path=file_path,
                filename=v.file_name,
                media_type=v.mime_type or "application/octet-stream",
            )

    raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản yêu cầu.")


@router.get("/edit/{material_id}", response_class=HTMLResponse)
def edit_form(material_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    courses = course_material_service.get_all_courses(db)

    return render_template(
        request,
        "course_material/edit.html",
        {
            "material": material,
            "courses": courses,
            "error": None,
            "page_title": "✏️ Chỉnh sửa tài liệu",
        },
    )


@router.post("/edit/{material_id}", response_class=HTMLResponse)
async def update_material(
    material_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    ensure_admin(request)

    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    courses = course_material_service.get_all_courses(db)

    try:
        await course_material_service.update_material(
            db=db,
            material_id=material_id,
            title=title,
            description=description,
            file=file,
        )

        message = quote("Cập nhật tài liệu thành công.")
        return RedirectResponse(f"/admin/course-material/list?success={message}", status_code=303)

    except Exception as e:
        material.title = title
        material.description = description or ""
        return render_template(
            request,
            "course_material/edit.html",
            {
                "material": material,
                "courses": courses,
                "error": str(e),
                "page_title": "✏️ Chỉnh sửa tài liệu",
            },
            status_code=400,
        )


@router.get("/delete/{material_id}", response_class=HTMLResponse)
def delete_confirm(material_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    material = course_material_service.get_by_id(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    versions = course_material_service.get_versions(db, material_id)

    return render_template(
        request,
        "course_material/delete.html",
        {
            "material": material,
            "versions": versions,
            "page_title": "🗑️ Xóa tài liệu",
        },
    )


@router.post("/delete/{material_id}")
def delete_material(material_id: str, request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)

    try:
        course_material_service.delete_material(db, material_id)
        message = quote("Xóa tài liệu thành công.")
        return RedirectResponse(f"/admin/course-material/list?success={message}", status_code=303)
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(f"/admin/course-material/list?error={message}", status_code=303)
    except Exception as e:
        message = quote(str(e))
        return RedirectResponse(f"/admin/course-material/list?error={message}", status_code=303)