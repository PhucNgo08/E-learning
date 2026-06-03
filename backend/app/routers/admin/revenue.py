"""
==========================================================
💰 ROUTER: Admin - Revenue Management
Quản lý doanh thu VNPay và ví nội bộ
==========================================================
"""

import traceback

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.config.template_config import get_template_by_path
from app.services.admin.revenue_service import (
    get_revenue_summary,
    get_recent_paid_orders,
)


router = APIRouter(
    prefix="/admin/revenue",
    tags=["Admin - Revenue"],
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    templates = get_template_by_path(request.url.path)

    base_context = {
        "request": request,
        "active_page": "revenue",
        "page_title": "💰 Quản lý doanh thu",
    }
    base_context.update(context)

    return templates.TemplateResponse(
        template_name,
        base_context,
        status_code=status_code,
    )


@router.get("/dashboard", response_class=HTMLResponse)
def revenue_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        summary = get_revenue_summary(db)
        recent_orders = get_recent_paid_orders(db, limit=20)

        username = (
            getattr(current_user, "username", None)
            or request.session.get("username")
            or "Quản trị viên"
        )

        return render_template(
            request,
            "revenue/dashboard.html",
            {
                "username": username,
                "summary": summary,
                "recent_orders": recent_orders,
                "page_title": "💰 Quản lý doanh thu",
            },
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse(
            f"<pre style='color:red'>{traceback.format_exc()}</pre>",
            status_code=500,
        )