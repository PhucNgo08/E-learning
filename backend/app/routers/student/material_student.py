"""
==========================================================
🎓 ROUTER: Student - Materials
Hiển thị danh sách, chi tiết và tải tài liệu học tập
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from starlette import status

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
# 🏠 1️⃣ Trang tổng hợp tất cả tài liệu (mặc định)
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def all_materials(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách tất cả tài liệu công khai.
    """
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


# ======================================================
# 📘 2️⃣ Danh sách tài liệu theo khóa học
# ======================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_materials(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách tài liệu của một khóa học cụ thể.
    """
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


# ======================================================
# 🔍 3️⃣ Xem chi tiết tài liệu
# ======================================================
@router.get("/detail/{material_id}", response_class=HTMLResponse)
async def material_detail(request: Request, material_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị thông tin chi tiết của một tài liệu học tập.
    """
    material = material_service.get_material_detail(db, material_id)
    if not material:
        return HTMLResponse("❌ Không tìm thấy tài liệu.", status_code=status.HTTP_404_NOT_FOUND)

    return templates["student"].TemplateResponse(
        "material/detail.html",
        {
            "request": request,
            "material": material,
            "page_title": f"📄 Chi tiết tài liệu - {material.title}",
            "active_page": "material"
        },
    )


# ======================================================
# ⬇️ 4️⃣ Tải xuống tài liệu
# ======================================================
@router.get("/download/{material_id}", response_class=HTMLResponse)
async def download_material(request: Request, material_id: str, db: Session = Depends(get_db)):
    """
    Khi sinh viên tải file: cập nhật lượt tải xuống và hiển thị thông báo.
    """
    material = material_service.increment_download_count(db, material_id)
    if not material:
        return HTMLResponse("❌ Tài liệu không tồn tại.", status_code=status.HTTP_404_NOT_FOUND)

    return templates["student"].TemplateResponse(
        "material/download.html",
        {
            "request": request,
            "material": material,
            "page_title": f"⬇️ Tải xuống tài liệu - {material.title}",
            "active_page": "material"
        },
    )
