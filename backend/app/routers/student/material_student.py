"""
==========================================================
🎓 ROUTER: Student - Materials (Enrollment-based Access)
==========================================================
"""

from pathlib import Path
import traceback

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.paths import UPLOADS_BASE
from app.config.template_config import templates
from app.database.connection import get_db
from app.services.student import material_service

router = APIRouter(
    prefix="/student/material",
    tags=["Student - Materials"]
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


@router.get("/", response_class=HTMLResponse)
async def all_materials(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        materials = material_service.get_public_materials(db)

        return templates["student"].TemplateResponse(
            "material/list.html",
            {
                "request": request,
                "materials": materials,
                "page_title": "📚 Tất cả tài liệu học tập",
                "active_page": "material",
            },
        )

    except Exception as e:
        print("❌ [Material][ListAll]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải danh sách tài liệu.", status_code=500)


@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_materials(request: Request, course_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        if not material_service.student_can_access_material(db, user_id, course_id):
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền xem tài liệu của khóa học này."},
                status_code=403,
            )

        materials = material_service.get_materials_by_course(db, course_id, user_id)

        return templates["student"].TemplateResponse(
            "material/list.html",
            {
                "request": request,
                "materials": materials,
                "course_id": course_id,
                "page_title": "📘 Tài liệu khóa học",
                "active_page": "material",
            },
        )

    except Exception as e:
        print("❌ [Material][ByCourse]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải tài liệu khóa học.", status_code=500)


@router.get("/detail/{material_id}", response_class=HTMLResponse)
async def material_detail(request: Request, material_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        material = material_service.get_material_detail(db, material_id, user_id)
        if not material:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy tài liệu hoặc bạn không có quyền xem."},
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "material/detail.html",
            {
                "request": request,
                "material": material,
                "page_title": f"📄 {material.title}",
                "active_page": "material",
            },
        )

    except Exception as e:
        print("❌ [Material][Detail]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi xem chi tiết tài liệu.", status_code=500)


@router.get("/download/{material_id}")
async def download_material(request: Request, material_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        material = material_service.get_material_detail(db, material_id, user_id)
        if not material:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Tài liệu không tồn tại hoặc bạn không có quyền tải."},
                status_code=404,
            )

        material_service.increment_download_count(db, material_id)

        file_url = (material.file_url or "").strip()
        if file_url.startswith(("http://", "https://")):
            return RedirectResponse(file_url, status_code=302)

        file_path = material_service.resolve_material_file_path(material, UPLOADS_BASE)

        if not file_path:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ File không tồn tại trên hệ thống."},
                status_code=404,
            )

        print(f"⬇️ [Material][Download] User={user_id} tải {file_path.name}")

        return FileResponse(
            path=str(file_path),
            filename=material.file_name or Path(file_path).name,
            media_type=material.mime_type or "application/octet-stream",
        )

    except Exception as e:
        db.rollback()
        print("❌ [Material][Download]:", e)
        traceback.print_exc()
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Không thể tải file."},
            status_code=400,
        )


@router.get("/favorites", response_class=HTMLResponse)
async def favorite_materials(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    try:
        favorites = material_service.get_favorite_materials(db, user_id)

        return templates["student"].TemplateResponse(
            "material/favorites.html",
            {
                "request": request,
                "materials": favorites,
                "page_title": "⭐ Tài liệu yêu thích",
                "active_page": "material",
            },
        )

    except Exception as e:
        print("❌ [Material][Favorites]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải tài liệu yêu thích.", status_code=500)