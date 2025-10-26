"""
==========================================================
🎯 ROUTER: Admin - Dashboard
Hiển thị trang bảng điều khiển (dashboard) cho quản trị viên
==========================================================
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

# ✅ Import cấu hình template động
from app.config.template_config import get_template_by_path

# ✅ Import kết nối DB
from app.database.connection import get_db


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
dashboard_router = APIRouter(
    prefix="/admin",
    tags=["Admin - Dashboard"]
)


# ======================================================
# 🧭 Trang Dashboard Admin
# ======================================================
@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Trang quản trị Admin - hiển thị Dashboard tổng quan.
    """

    # 🧠 Lấy thông tin đăng nhập từ session
    user_role = request.session.get("role")
    username = request.session.get("username")

    # 🔒 Kiểm tra quyền truy cập
    if not user_role:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập để truy cập trang này.")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập trang này.")

    # ✅ Lấy template tương ứng theo đường dẫn (admin → templates["admin"])
    templates = get_template_by_path(request.url.path)

    # ======================================================
    # 📊 Giả lập dữ liệu thống kê (có thể truy vấn thực tế từ DB)
    # ======================================================
    stats = {
        "total_users": 152,
        "total_courses": 34,
        "total_lessons": 180,
        "total_teachers": 12,
        "total_students": 120,
    }

    # ✅ Danh sách khóa học mẫu
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

    # ======================================================
    # 🖼️ Render giao diện Dashboard
    # ======================================================
    return templates.TemplateResponse(
        "admin_dashboard.html",  # ⚠️ chỉ cần tên file, vì template admin đã được trỏ sẵn
        {
            "request": request,
            "username": username,
            "active_page": "dashboard",
            "stats": stats,
            "courses": courses,
        },
    )
