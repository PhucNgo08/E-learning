"""
==========================================================
🔐 AUTH - LOGIN ROUTER (PRO MAX ENTERPRISE v3.6 FINAL – FIXED)
✔ Login Web (session middleware)
✔ Login Postman (JSON + Set-Cookie)
✔ Chống brute-force
✔ Remember me (7 ngày)
✔ Auto-create Wallet cho Student khi login LẦN ĐẦU (OPTION A)
✔ FIX role/user_role — Không còn lỗi 401
==========================================================
"""

import logging
import hashlib
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.security_setting import SecuritySettings
from app.services.common.password_service import verify_password
from app.config.template_config import templates

# 🟢 Wallet (OPTION A)
from app.services.wallet_service import get_wallet, create_wallet


login_router = APIRouter(prefix="/auth", tags=["Auth - Login"])
logger = logging.getLogger("auth_login")
logger.setLevel(logging.INFO)


# ======================================================
# 🔍 Lấy user theo username/email
# ======================================================
def get_user_by_identifier(db: Session, identifier: str) -> User | None:
    identifier = identifier.strip().lower()

    if "@" in identifier:
        return db.query(User).filter(User.email == identifier).first()

    return db.query(User).filter(User.username == identifier).first()


# ======================================================
# 🔐 Kiểm tra password
# ======================================================
def check_credentials(user: User, password: str) -> bool:
    if not user or not user.password_hash:
        return False

    hashed = user.password_hash

    # bcrypt
    if hashed.startswith("$2a$") or hashed.startswith("$2b$"):
        return verify_password(password, hashed)

    # SHA256 legacy
    return hashlib.sha256(password.encode()).hexdigest() == hashed


# ======================================================
# 🔄 HIỂN THỊ FORM LOGIN (WEB)
# ======================================================
@login_router.get("/login", response_class=HTMLResponse)
async def show_login(request: Request, error: Optional[str] = None):

    # 🔥 Quan trọng: ưu tiên user_role để đồng bộ middlewares
    role = request.session.get("user_role") or request.session.get("role")

    redirect_map = {
        "admin": "/admin/dashboard",
        "teacher": "/teacher/dashboard",
        "student": "/student/dashboard",
    }

    if role in redirect_map:
        return RedirectResponse(redirect_map[role], status_code=303)

    return templates["auth"].TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )


# ======================================================
# 🔐 SUBMIT LOGIN — WEB + POSTMAN
# ======================================================
@login_router.post("/login")
async def do_login(
    request: Request,
    db: Session = Depends(get_db),

    username: str = Form(None),
    email: str = Form(None),
    identifier: str = Form(None),
    password: str = Form(...),
    remember_me: Optional[str] = Form(None),
):
    """
    Hỗ trợ login Web + Postman
    """

    # ======================================================
    # 🔍 Xác định login_id
    # ======================================================
    login_id = identifier or username or email
    if not login_id:
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Vui lòng nhập email hoặc username."}
        )

    user = get_user_by_identifier(db, login_id)
    if not user:
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Tài khoản không tồn tại."}
        )

    # ======================================================
    # 🔒 Bảo mật: giới hạn đăng nhập sai
    # ======================================================
    security = db.query(SecuritySettings).filter_by(user_id=user.id).first()
    if not security:
        security = SecuritySettings(user_id=user.id)
        db.add(security)
        db.commit()
        db.refresh(security)

    if security.account_locked_until and security.account_locked_until > datetime.utcnow():
        lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request,
             "error": f"🔒 Tài khoản bị khóa đến {lock_time}."}
        )

    # ======================================================
    # 🔑 Check password
    # ======================================================
    if not check_credentials(user, password):

        security.failed_login_attempts += 1

        if security.failed_login_attempts >= 5:
            security.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            security.failed_login_attempts = 0
            db.commit()

            lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
            return templates["auth"].TemplateResponse(
                "login.html",
                {"request": request,
                 "error": f"🔒 Sai 5 lần — tài khoản bị khóa đến {lock_time}."}
            )

        db.commit()

        remaining = 5 - security.failed_login_attempts
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request,
             "error": f"⚠️ Mật khẩu sai. Còn {remaining} lần thử."}
        )

    # ======================================================
    # 🔍 Kiểm tra trạng thái user
    # ======================================================
    status = getattr(user.status, "value", str(user.status)).lower()
    if status not in ["active", "1", "true", "enabled"]:
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "🚫 Tài khoản đã bị vô hiệu hóa."}
        )

    # ======================================================
    # 🟢 LOGIN OK
    # ======================================================
    security.failed_login_attempts = 0
    security.account_locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    # ======================================================
    # 🌟 CREATE WALLET CHO STUDENT
    # ======================================================
    role_value = getattr(user.role, "value", user.role)

    if role_value == "student":
        wallet = get_wallet(db, user.id)
        if not wallet:
            create_wallet(db, user.id)

    # ======================================================
    # 🟢 TẠO SESSION — FIX PRO MAX 2025
    # ======================================================
    request.session.clear()

    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "Unknown-UA")

    expiry = (
        datetime.utcnow() + timedelta(days=7)
        if remember_me
        else datetime.utcnow() + timedelta(hours=6)
    )

    # ⭐⭐ FIX QUAN TRỌNG NHẤT: thêm user_role cho middleware + router
    request.session.update({
        "user_id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,

        "role": role_value,          # giữ nguyên để tránh lỗi UI
        "user_role": role_value,     # FIX — dùng cho auth dependencies & middleware

        "avatar": user.avatar_url or "/uploads/avatars/default-avatar.png",
        "session_ip": client_ip,
        "session_ua": user_agent,
        "expires_at": expiry.isoformat(),
        "last_active": datetime.utcnow().timestamp(),
    })

    # ======================================================
    # 🔀 REDIRECT THEO ROLE
    # ======================================================
    redirect_map = {
        "admin": "/admin/dashboard",
        "teacher": "/teacher/dashboard",
        "student": "/student/dashboard",
    }

    return RedirectResponse(redirect_map.get(role_value, "/"), status_code=303)


# ======================================================
# 🚪 LOGOUT
# ======================================================
@login_router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/auth/login", status_code=303)
