"""
==========================================================
🔐 AUTH - LOGIN ROUTER (PRO MAX ENTERPRISE v3.3)
Giữ nguyên logic cũ, bổ sung:
✔ Login bằng username / email / identifier (backward support)
✔ Chống brute-force: 5 lần → khóa 30 phút
✔ Session bảo mật nâng cao (IP + UserAgent bind)
✔ Remember me (7 ngày)
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
# 🔐 Kiểm tra password (bcrypt hoặc SHA256)
# ======================================================
def check_credentials(user: User, password: str) -> bool:
    if not user or not user.password_hash:
        return False

    hashed = user.password_hash

    # bcrypt
    if hashed.startswith("$2a$") or hashed.startswith("$2b$"):
        return verify_password(password, hashed)

    # legacy SHA256
    return hashlib.sha256(password.encode()).hexdigest() == hashed


# ======================================================
# 🔄 HIỂN THỊ FORM LOGIN
# ======================================================
@login_router.get("/login", response_class=HTMLResponse)
async def show_login(request: Request, error: Optional[str] = None):

    if (role := request.session.get("role")):
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
# 🔐 SUBMIT LOGIN
# ======================================================
@login_router.post("/login", response_class=HTMLResponse)
async def do_login(
    request: Request,
    db: Session = Depends(get_db),

    username: str = Form(None),
    email: str = Form(None),
    identifier: str = Form(None),   # hỗ trợ template cũ
    password: str = Form(...),
    remember_me: Optional[str] = Form(None)  # ✔ NEW
):
    """
    Hỗ trợ login bằng:
    - username
    - email
    - identifier (template cũ)
    """

    login_id = identifier or username or email

    if not login_id:
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Vui lòng nhập email hoặc username."}
        )

    logger.info(f"🔐 Login attempt: {login_id}")

    # === Lấy user
    user = get_user_by_identifier(db, login_id)

    if not user:
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Tài khoản không tồn tại."}
        )

    # === Lấy SecuritySettings (hoặc tạo mới)
    security = db.query(SecuritySettings).filter_by(user_id=user.id).first()
    if not security:
        security = SecuritySettings(user_id=user.id)
        db.add(security)
        db.commit()
        db.refresh(security)

    # === Kiểm tra khóa tạm thời
    if security.account_locked_until and security.account_locked_until > datetime.utcnow():
        lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": f"🔒 Tài khoản bị khóa đến {lock_time}."}
        )

    # === Kiểm tra mật khẩu
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
                 "error": f"🔒 Sai mật khẩu quá 5 lần — bị khóa đến {lock_time}."}
            )

        db.commit()
        remaining = 5 - security.failed_login_attempts

        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request,
             "error": f"⚠️ Mật khẩu không đúng. Còn {remaining} lần thử."}
        )

    # === Check account status
    status = getattr(user.status, "value", str(user.status)).lower()
    if status not in ["active", "1", "true", "enabled"]:
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "🚫 Tài khoản đã bị vô hiệu hóa."}
        )

    # === Login ok
    security.failed_login_attempts = 0
    security.account_locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    # ======================================================
    # 🟢 TẠO SESSION (PRO MAX)
    # ======================================================
    request.session.clear()

    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "Unknown-UA")

    expiry = (
        datetime.utcnow() + timedelta(days=7)
        if remember_me
        else datetime.utcnow() + timedelta(hours=6)
    )

    request.session.update({
        "user_id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": getattr(user.role, "value", user.role),
        "avatar": user.avatar_url or "/uploads/avatars/default-avatar.png",

        # security
        "session_ip": client_ip,
        "session_ua": user_agent,
        "expires_at": expiry.isoformat(),
        "last_active": datetime.utcnow().timestamp(),
    })

    logger.info(f"🎯 Login success: {user.username} | RememberMe={bool(remember_me)}")

    redirect_map = {
        "admin": "/admin/dashboard",
        "teacher": "/teacher/dashboard",
        "student": "/student/dashboard",
    }

    return RedirectResponse(redirect_map.get(request.session["role"], "/"), status_code=303)


# ======================================================
# 🚪 LOGOUT
# ======================================================
@login_router.get("/logout")
async def logout(request: Request):
    username = request.session.get("username", "Unknown")
    request.session.clear()
    logger.info(f"🚪 Logged out: {username}")
    return RedirectResponse("/auth/login", status_code=303)
