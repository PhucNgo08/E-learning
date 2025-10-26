"""
==========================================================
📊 ROUTER: Teacher - Statistics
Hiển thị thống kê tổng quan cho giáo viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

# ✅ Import nội bộ
from app.database.connection import get_db
from app.services.teacher import statistics_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path


# ======================================================
# 🚀 Router
# ======================================================
router = APIRouter(
    prefix="/teacher/statistics",
    tags=["Teacher - Statistics"]
)


# ======================================================
# 🧭 0️⃣ Redirect gốc → /index
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_statistics_root():
    """Chuyển /teacher/statistics → /teacher/statistics/index"""
    return RedirectResponse("/teacher/statistics/index", status_code=303)


# ======================================================
# 📈 1️⃣ Trang thống kê giáo viên
# ======================================================
@router.get("/index", response_class=HTMLResponse)
def teacher_statistics(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị trang thống kê tổng quan cho giáo viên"""
    teacher = current_teacher

    # 📊 Lấy dữ liệu thống kê tổng quan từ service
    data = statistics_service.get_teacher_statistics(db, teacher.id)

    # ✅ Chọn template tự động dựa theo route
    templates = get_template_by_path(str(request.url.path))

    return templates.TemplateResponse(
        "statistics/index.html",
        {
            "request": request,
            "teacher": teacher,
            "data": data,
            "page_title": "📊 Thống kê tổng quan",
            "now": datetime.now(),
        },
    )
