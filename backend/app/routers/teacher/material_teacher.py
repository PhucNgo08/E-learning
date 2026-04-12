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
from datetime import datetime

from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_teacher
from app.services.teacher import material_teacher_service as material_service

router = APIRouter(
    prefix="/teacher/materials",
    tags=["Teacher - Materials"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "now": datetime.now(),
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    return RedirectResponse("/teacher/materials/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
async def list_materials(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    materials = material_service.get_all(db, teacher.id)
    stats = material_service.get_statistics(db, teacher.id)

    return render_template(
        request,
        "materials/list.html",
        {
            "teacher": teacher,
            "materials": materials,
            "stats": stats,
            "page_title": "📂 Danh sách tài liệu khóa học",
        },
    )


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    courses = material_service.get_courses_by_teacher(db, teacher.id)

    return render_template(
        request,
        "materials/upload.html",
        {
            "teacher": teacher,
            "courses": courses,
            "page_title": "📤 Upload tài liệu khóa học",
        },
    )


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


@router.get("/edit/{material_id}", response_class=HTMLResponse)
async def edit_material_form(
    material_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher
    material = material_service.get_by_id(db, teacher.id, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu hoặc không có quyền truy cập.")

    return render_template(
        request,
        "materials/edit.html",
        {
            "teacher": teacher,
            "material": material,
            "page_title": "✏️ Chỉnh sửa tài liệu",
        },
    )


@router.post("/edit/{material_id}")
async def edit_material(
    material_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile | None = File(None),
):
    teacher = current_teacher
    result = await material_service.update_material(
        db, teacher.id, material_id, title, description, file
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/materials/list", status_code=303)


@router.post("/delete/{material_id}")
async def delete_material(
    material_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    result = material_service.delete_material(db, teacher.id, material_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/materials/list", status_code=303)
@router.get("/delete/{material_id}", response_class=HTMLResponse)
async def delete_material_form(
    material_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher
    material = material_service.get_by_id(db, teacher.id, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu hoặc không có quyền truy cập.")

    return render_template(
        request,
        "materials/delete.html",
        {
            "teacher": teacher,
            "material": material,
            "page_title": "🗑️ Xóa tài liệu",
        },
    )