from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# ✅ Khởi tạo router với prefix /admin
dashboard_router = APIRouter(prefix="/admin", tags=["Admin - Dashboard"])

# ✅ Đường dẫn thư mục template
templates = Jinja2Templates(directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin")

@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Trang quản trị admin - hiển thị dashboard"""

    # Lấy thông tin từ session (nếu có)
    user_role = request.session.get("role")
    username = request.session.get("username")

    if not user_role:
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập để truy cập trang này.")
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập trang này.")

    # ✅ Render template
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "username": username,
            "active_page": "dashboard"
        }
    )
