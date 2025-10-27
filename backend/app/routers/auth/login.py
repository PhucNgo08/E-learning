"""
==========================================================
🔐 ROUTER: AUTH - LOGIN
Xử lý đăng nhập người dùng (Admin / Teacher / Student)
==========================================================
"""

import hashlib
import logging
import traceback
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

# ✅ Import database & service
from app.database.connection import get_db
from app.models.user import User
from app.services.common.password_service import verify_password

# ✅ Import cấu hình template
from app.config.template_config import templates

# ==========================================================
# ⚙️ Cấu hình Router & Logger
# ==========================================================
login_router = APIRouter(prefix="/auth", tags=["Auth - Login"])
logger = logging.getLogger("auth_login")
logger.setLevel(logging.INFO)


# ==========================================================
# 🧩 XÁC THỰC NGƯỜI DÙNG
# ==========================================================
def authenticate_user(db: Session, username: str, password: str):
    """
    ✅ Hỗ trợ hash cũ SHA256 & hash mới bcrypt.
    Trả về đối tượng User nếu đúng,
    hoặc chuỗi "username"/"password" nếu sai.
    """
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return "username"

        hashed_pw = user.password_hash or ""
        # bcrypt hash
        if hashed_pw.startswith("$2b$") or hashed_pw.startswith("$2a$"):
            valid = verify_password(password, hashed_pw)
        else:
            valid = hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed_pw

        return user if valid else "password"

    except Exception as e:
        logger.error(f"💥 Lỗi xác thực người dùng: {e}")
        traceback.print_exc()
        return None


# ==========================================================
# 🪪 GET /auth/login — Hiển thị form đăng nhập
# ==========================================================
@login_router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: Optional[str] = None):
    """Hiển thị form đăng nhập hoặc redirect nếu đã có session hợp lệ."""
    role = request.session.get("role")

    if role == "admin":
        return RedirectResponse("/admin/dashboard", status_code=303)
    if role == "teacher":
        return RedirectResponse("/teacher/dashboard", status_code=303)
    if role == "student":
        return RedirectResponse("/student/dashboard", status_code=303)

    return templates["auth"].TemplateResponse(
        "login.html",
        {"request": request, "error": error, "page_title": "🔑 Đăng nhập"},
    )


# ==========================================================
# 🔐 POST /auth/login — Xử lý đăng nhập
# ==========================================================
@login_router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """Kiểm tra username/password và ghi session."""
    logger.info(f"🔐 Đăng nhập thử: {username}")

    auth_result = authenticate_user(db, username, password)

    if auth_result == "username":
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Tên đăng nhập không tồn tại."},
        )

    if auth_result == "password":
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "⚠️ Mật khẩu không đúng."},
        )

    if isinstance(auth_result, User):
        user = auth_result

        # ✅ Clear session cũ
        request.session.clear()

        # ✅ Tạo session mới
        request.session.update({
            "user_id": str(user.id),
            "username": user.username,
            "role": getattr(user.role, "value", str(user.role)),
        })

        logger.info(f"🎯 Đăng nhập thành công: {user.username} ({user.role})")

        # 🚀 Chuyển hướng theo role
        redirect_map = {
            "admin": "/admin/dashboard",
            "teacher": "/teacher/dashboard",
            "student": "/student/dashboard",
        }
        return RedirectResponse(redirect_map.get(user.role, "/"), status_code=303)

    # 💥 Nếu đến đây là có lỗi ngoài ý muốn
    logger.error("Lỗi xác thực ngoài ý muốn.")
    return templates["auth"].TemplateResponse(
        "login.html",
        {"request": request, "error": "⚠️ Có lỗi hệ thống, vui lòng thử lại."},
    )


# ==========================================================
# 🚪 GET /auth/logout — Đăng xuất
# ==========================================================
@login_router.get("/logout")
async def logout(request: Request):
    """Xóa session và quay lại trang đăng nhập."""
    username = request.session.get("username", "Unknown")
    logger.info(f"🚪 Đăng xuất: {username}")
    request.session.clear()
    return RedirectResponse("/auth/login", status_code=303)
