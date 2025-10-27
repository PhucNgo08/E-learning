from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas import UserResponse

# ✅ Dùng template config chung (thay vì hard-code directory)
from app.config.template_config import get_template_by_path

# ============================================================
# 🚀 Router
# ============================================================
register_router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

# ============================================================
# 📝 1️⃣ Trang đăng ký tài khoản
# ============================================================
@register_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Hiển thị trang đăng ký tài khoản"""
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "auth/register.html",
        {"request": request, "page_title": "📝 Đăng ký tài khoản"}
    )

# ============================================================
# 👤 2️⃣ Lấy thông tin người dùng theo ID (API)
# ============================================================
@register_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """API lấy thông tin chi tiết người dùng theo ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="❌ Không tìm thấy người dùng.")
    return user
