"""
==========================================================
🎓 ROUTER: Student - Materials (FULL 100% PRODUCTION)
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from pathlib import Path
import traceback

from app.config.template_config import templates
from app.database.connection import get_db
from app.services.student import material_service
from app.models.course_material import CourseMaterial
from app.config.paths import UPLOADS_BASE  # <-- Quan trọng: để tải file đúng


router = APIRouter(
    prefix="/student/material",
    tags=["Student - Materials"]
)


# ======================================================
# 🏠 1) Tất cả tài liệu công khai
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def all_materials(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        materials = (
            db.query(CourseMaterial)
            .filter(CourseMaterial.is_public == 1)
            .order_by(CourseMaterial.created_at.desc())
            .all()
        )

        return templates["student"].TemplateResponse(
            "material/list.html",
            {
                "request": request,
                "materials": materials,
                "page_title": "📚 Tất cả tài liệu học tập",
                "active_page": "material"
            },
        )

    except Exception as e:
        print("❌ [Material][ListAll]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải danh sách tài liệu.", 500)


# ======================================================
# 📘 2) Danh sách tài liệu theo khóa học
# ======================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_materials(request: Request, course_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        # TODO: check khóa học đã đăng ký
        materials = material_service.get_materials_by_course(db, course_id)

        return templates["student"].TemplateResponse(
            "material/list.html",
            {
                "request": request,
                "materials": materials,
                "course_id": course_id,
                "page_title": "📘 Tài liệu khóa học",
                "active_page": "material"
            },
        )

    except Exception as e:
        print("❌ [Material][ByCourse]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải tài liệu khóa học.", 500)


# ======================================================
# 🔍 3) Xem chi tiết tài liệu
# ======================================================
@router.get("/detail/{material_id}", response_class=HTMLResponse)
async def material_detail(request: Request, material_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        material = material_service.get_material_detail(db, material_id)
        if not material:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy tài liệu hoặc tài liệu đã hết hạn."},
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "material/detail.html",
            {
                "request": request,
                "material": material,
                "page_title": f"📄 {material.title}",
                "active_page": "material"
            },
        )

    except Exception as e:
        print("❌ [Material][Detail]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi xem chi tiết tài liệu.", 500)


# ======================================================
# ⬇️ 4) Tải file tài liệu (FileResponse)
# ======================================================
@router.get("/download/{material_id}")
async def download_material(request: Request, material_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        material = material_service.increment_download_count(db, material_id)
        if not material:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Tài liệu không tồn tại."},
                status_code=404,
            )

        # 🔥 FIX: file_url là URL, không phải đường tuyệt đối.
        # Ta sẽ kết hợp với UPLOADS_BASE để tìm file thực tế.
        file_path = Path(UPLOADS_BASE) / material.file_name

        if not file_path.exists():
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ File không tồn tại trên hệ thống."},
                status_code=404,
            )

        print(f"⬇️ [Material][Download] User={user_id} tải {material.file_name}")

        return FileResponse(
            path=str(file_path),
            filename=material.file_name,
            media_type=material.mime_type or "application/octet-stream"
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


# ======================================================
# ⭐ 5) Danh sách yêu thích (mock)
# ======================================================
@router.get("/favorites", response_class=HTMLResponse)
async def favorite_materials(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        favorites = material_service.get_favorite_materials(db, user_id)

        return templates["student"].TemplateResponse(
            "material/favorites.html",
            {
                "request": request,
                "materials": favorites,
                "page_title": "⭐ Tài liệu yêu thích",
                "active_page": "material"
            },
        )

    except Exception as e:
        print("❌ [Material][Favorites]:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải tài liệu yêu thích.", 500)
