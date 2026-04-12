import traceback

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.services.admin.user_statistics_service import get_user_statistics
from app.services.admin.course_overview_service import get_course_overview
from app.services.admin.review_stats_service import get_review_statistics
from app.config.template_config import get_template_by_path

statistics_router = APIRouter(
    prefix="/admin/statistics",
    tags=["Admin - Statistics"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "page_title": "📊 Bảng điều khiển thống kê",
        "active_page": "statistics",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@statistics_router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Hiển thị dashboard thống kê tổng quan hệ thống.
    """
    try:
        user_stats = get_user_statistics(db)
        course_stats = get_course_overview(db)
        review_stats = get_review_statistics(db)

        return render_template(
            request,
            "statistics/dashboard.html",
            {
                "user_stats": user_stats,
                "course_stats": course_stats,
                "review_stats": review_stats,
                "page_title": "📊 Bảng điều khiển thống kê",
            },
        )
    except Exception:
        print("\n❌ LỖI TẢI DASHBOARD THỐNG KÊ:\n", traceback.format_exc())
        return HTMLResponse(
            f"<pre>{traceback.format_exc()}</pre>",
            status_code=500,
        )