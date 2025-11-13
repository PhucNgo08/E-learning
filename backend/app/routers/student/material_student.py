"""
==========================================================
🎓 ROUTER: Student - Materials
Hoàn thiện đầy đủ chức năng tài liệu học tập cho sinh viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from pathlib import Path
import traceback

# ✅ Import cấu hình hệ thống
from app.config.template_config import templates
from app.database.connection import get_db

# ✅ Import service xử lý
from app.services.student import material_service
from app.models.course_material import CourseMaterial


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/student/material",
    tags=["Student - Materials"]
)


# ======================================================
# 🏠 1️⃣ Trang tổng hợp tất cả tài liệu công khai
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def all_materials(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách tất cả tài liệu công khai."""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

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
        print("❌ [Material][ListAll] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách tài liệu.</h4>", status_code=500)


# ======================================================
# 📘 2️⃣ Danh sách tài liệu theo khóa học
# ======================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_materials(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị danh sách tài liệu của một khóa học cụ thể."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
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
        print("❌ [Material][ByCourse] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải tài liệu khóa học.</h4>", status_code=500)


# ======================================================
# 🔍 3️⃣ Xem chi tiết tài liệu
# ======================================================
@router.get("/detail/{material_id}", response_class=HTMLResponse)
async def material_detail(request: Request, material_id: str, db: Session = Depends(get_db)):
    """Hiển thị thông tin chi tiết của một tài liệu học tập."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        material = material_service.get_material_detail(db, material_id)
        if not material:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy tài liệu."},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return templates["student"].TemplateResponse(
            "material/detail.html",
            {
                "request": request,
                "material": material,
                "page_title": f"📄 Chi tiết tài liệu - {material.title}",
                "active_page": "material"
            },
        )

    except Exception as e:
        print("❌ [Material][Detail] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xem chi tiết tài liệu.</h4>", status_code=500)


# ======================================================
# ⬇️ 4️⃣ Tải xuống tài liệu (FileResponse thực tế)
# ======================================================
@router.get("/download/{material_id}")
async def download_material(request: Request, material_id: str, db: Session = Depends(get_db)):
    """Khi sinh viên tải file: cập nhật lượt tải & trả về file thực tế."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        material = material_service.increment_download_count(db, material_id)
        if not material:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Tài liệu không tồn tại."},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        file_path = Path(material.file_url or "")
        if not file_path.exists():
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ File không còn tồn tại trên hệ thống."},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        print(f"⬇️ [Material][Download] User={user_id} tải file {material.file_name}")
        return FileResponse(
            path=file_path,
            filename=material.file_name,
            media_type="application/octet-stream"
        )

    except Exception as e:
        db.rollback()
        print("❌ [Material][Download] Lỗi:", e)
        traceback.print_exc()
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Không thể tải file. Vui lòng thử lại."},
            status_code=400,
        )


# ======================================================
# ⭐ 5️⃣ Danh sách tài liệu yêu thích (tùy chọn)
# ======================================================
@router.get("/favorites", response_class=HTMLResponse)
async def favorite_materials(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách tài liệu học viên đã đánh dấu yêu thích."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

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
        print("❌ [Material][Favorites] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách tài liệu yêu thích.</h4>", status_code=500)
