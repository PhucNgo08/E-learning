from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database.connection import get_db
from KHoaHocOnline.backend.app.services.admin.user_statistics_service import get_user_statistics
from app.services.admin.course_overview_service import get_course_overview
from app.services.admin.review_stats_service import get_review_statistics

# ==============================
# 📁 Template cấu hình
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/Account"
)

# ==============================
# 🚀 Khởi tạo router
# ==============================
statistics_router = APIRouter(
    prefix="/admin/statistics",
    tags=["Admin - Statistics"]
)

# =========================================================
# 📊 Dashboard thống kê tổng hợp
# =========================================================
@statistics_router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Hiển thị trang dashboard tổng quan hệ thống"""
    try:
        user_stats = get_user_statistics(db)
        context = {
            "request": request,
            "user_stats": user_stats,
            "page_title": "📊 Bảng điều khiển thống kê"
        }
        return templates.TemplateResponse("dashboard.html", context)
    except Exception as e:
        return HTMLResponse(f"Lỗi khi tải dashboard: {e}", status_code=500)
