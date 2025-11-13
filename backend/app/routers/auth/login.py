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
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.security_setting import SecuritySettings  # ✅ Model bảo mật

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
# 🧩 HÀM XÁC THỰC NGƯỜI DÙNG
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
        # ✅ Kiểm tra bcrypt hoặc hash cũ SHA256
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
    """Hiển thị form đăng nhập hoặc chuyển hướng nếu đã đăng nhập."""
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
    """Xử lý đăng nhập người dùng, có kiểm tra khóa tạm thời."""
    logger.info(f"🔐 Đăng nhập thử: {username}")

    # --- Tìm user ---
    user = db.query(User).filter(User.username == username).first()
    security = None

    # Nếu có user, đảm bảo có record trong bảng security_settings
    if user:
        security = db.query(SecuritySettings).filter(SecuritySettings.user_id == user.id).first()
        if not security:
            security = SecuritySettings(user_id=user.id)
            db.add(security)
            db.commit()
            db.refresh(security)

        # 🔒 Nếu tài khoản đang bị khóa tạm thời
        if security.account_locked_until and security.account_locked_until > datetime.utcnow():
            lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
            return templates["auth"].TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": f"🔒 Tài khoản đang bị khóa tạm thời đến {lock_time}.",
                },
            )

    # --- Xác thực tài khoản ---
    auth_result = authenticate_user(db, username, password)

    # ❌ Không tồn tại username
    if auth_result == "username":
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Tên đăng nhập không tồn tại."},
        )

    # ⚠️ Sai mật khẩu
    if auth_result == "password":
        if user and security:
            security.failed_login_attempts += 1

            # Nếu sai >= 5 lần → khóa 30 phút
            if security.failed_login_attempts >= 5:
                security.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
                security.failed_login_attempts = 0
                db.commit()
                lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
                return templates["auth"].TemplateResponse(
                    "login.html",
                    {
                        "request": request,
                        "error": f"🔒 Sai mật khẩu quá 5 lần — tài khoản bị khóa đến {lock_time}.",
                    },
                )

            db.commit()

        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "⚠️ Mật khẩu không đúng."},
        )

    # ✅ Nếu xác thực hợp lệ
    if isinstance(auth_result, User):
        user = auth_result

        # 🧩 DEBUG — In ra thông tin thực tế của user
        print("🧩 DEBUG LOGIN:",
              "username=", user.username,
              "status=", repr(user.status),
              "type=", type(user.status),
              "role=", repr(user.role))

        # 🚫 Kiểm tra trạng thái tài khoản (đa kiểu an toàn)
       # Hỗ trợ Enum (StatusEnum.active / RoleEnum.admin)
        status_value = getattr(user.status, "value", str(user.status)).strip().lower()

        if status_value not in ["active", "1", "true", "enabled"]:
            print(f"⚠️ LOGIN BLOCKED: user.status={repr(user.status)} (converted={status_value})")
            return templates["auth"].TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "🚫 Tài khoản của bạn đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.",
                },
            )

        # 🔄 Reset bộ đếm khi đăng nhập đúng
        if security:
            security.failed_login_attempts = 0
            security.account_locked_until = None
            db.commit()

        # ✅ Clear session cũ, tạo session mới
        request.session.clear()
        request.session.update(
            {
                "user_id": str(user.id),
                "username": user.username,
                "role": getattr(user.role, "value", str(user.role)),
            }
        )

        logger.info(f"🎯 Đăng nhập thành công: {user.username} ({user.role})")

        redirect_map = {
            "admin": "/admin/dashboard",
            "teacher": "/teacher/dashboard",
            "student": "/student/dashboard",
        }
        return RedirectResponse(redirect_map.get(user.role, "/"), status_code=303)

    # 💥 Lỗi ngoài ý muốn
    logger.error("💥 Lỗi xác thực ngoài ý muốn.")
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
