"""
==========================================================
🎯 ROUTER: Admin - Dashboard (PRO MAX v2.0)
Hỗ trợ:
✔ Trình duyệt (Template)
✔ Postman (JSON)
✔ Kiểm tra session hợp lệ
==========================================================
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db


dashboard_router = APIRouter(
    prefix="/admin",
    tags=["Admin - Dashboard"]
)


@dashboard_router.get("/dashboard")
async def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản trị Admin - web + API support
    """

    user_role = request.session.get("role")
    username = request.session.get("username")

    # ===========================
    # 🔐 AUTH CHECK
    # ===========================
    if not user_role:
        # Nếu là Postman → trả JSON
        if "PostmanRuntime" in request.headers.get("User-Agent", ""):
            return JSONResponse(
                {"error": "Unauthorized — No session provided"},
                status_code=401
            )

        raise HTTPException(
            status_code=401,
            detail="Bạn cần đăng nhập để truy cập trang này."
        )

    if user_role != "admin":
        if "PostmanRuntime" in request.headers.get("User-Agent", ""):
            return JSONResponse(
                {"error": "Forbidden — Admin only"},
                status_code=403
            )

        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập trang này."
        )

    # ===========================
    # 📊 DATA MẪU
    # ===========================
    stats = {
        "total_users": 152,
        "total_courses": 34,
        "total_lessons": 180,
        "total_teachers": 12,
        "total_students": 120,
    }

    courses = [
        {
            "course_name": "Nhập môn Lập trình Python",
            "teacher_name": "Nguyễn Văn A",
            "status": "published",
            "created_at": "2025-10-01",
        },
        {
            "course_name": "Mạng máy tính nâng cao",
            "teacher_name": "Lê Thị B",
            "status": "draft",
            "created_at": "2025-09-20",
        },
    ]

    # ===========================
    # 🔥 Nếu là POSTMAN → trả JSON
    # ===========================
    if "PostmanRuntime" in request.headers.get("User-Agent", ""):
        return JSONResponse(
            {
                "status": "success",
                "username": username,
                "stats": stats,
                "courses": courses,
            }
        )

    # ===========================
    # 🖼️ TRẢ TEMPLATE CHO WEB
    # ===========================
    templates = get_template_by_path(request.url.path)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "username": username,
            "active_page": "dashboard",
            "stats": stats,
            "courses": courses,
        },
    )
