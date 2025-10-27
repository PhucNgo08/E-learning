from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db

# ✅ Import dịch vụ thống kê
from app.services.admin.user_statistics_service import get_user_statistics
from app.services.admin.course_overview_service import get_course_overview
from app.services.admin.review_stats_service import get_review_statistics

# ✅ Import hệ thống template dùng chung
from app.config.template_config import get_template_by_path

# ============================================================
# 🚀 Router
# ============================================================
statistics_router = APIRouter(
    prefix="/admin/statistics",
    tags=["Admin - Statistics"]
)

# ============================================================
# 📊 Dashboard thống kê tổng hợp
# ============================================================
@statistics_router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Hiển thị trang dashboard tổng quan hệ thống"""
    tpl = get_template_by_path(request.url.path)
    try:
        # 📈 Lấy dữ liệu thống kê người dùng, khóa học, đánh giá
        user_stats = get_user_statistics(db)
        course_stats = get_course_overview(db)
        review_stats = get_review_statistics(db)

        context = {
            "request": request,
            "user_stats": user_stats,
            "course_stats": course_stats,
            "review_stats": review_stats,
            "page_title": "📊 Bảng điều khiển thống kê"
        }

        return tpl.TemplateResponse("statistics/dashboard.html", context)
    except Exception as e:
        return HTMLResponse(f"<pre>Lỗi khi tải dashboard: {e}</pre>", status_code=500)
