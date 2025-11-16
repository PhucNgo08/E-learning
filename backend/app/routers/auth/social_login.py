"""
==========================================================
🔵 SOCIAL LOGIN ROUTER — Google + Microsoft (PRO MAX v3.2)
Giữ nguyên logic cũ, chỉ nâng cấp:
✔ Remember Me
✔ Auto-map role theo domain email
✔ Tối ưu session và bảo mật
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from decouple import config

from app.database.connection import get_db
from app.services.common.auth_service import (
    create_user_session,
    get_or_create_social_user,   # ⭐ Hàm mới trong auth_service
)

router = APIRouter(prefix="/auth", tags=["Auth - Social Login"])
oauth = OAuth()


# ======================================================
# GOOGLE LOGIN
# ======================================================
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"

oauth.register(
    name="google",
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_login(request: Request):
    """Chuyển hướng người dùng sang Google để đăng nhập."""
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Xử lý callback sau khi Google xác thực."""

    token = await oauth.google.authorize_access_token(request)
    info = token.get("userinfo")

    if not info:
        return RedirectResponse("/auth/login?error=Google+Login+Failed")

    email = info.get("email")
    full_name = info.get("name", "Người dùng Google")
    avatar = info.get("picture") or "/uploads/avatars/default-avatar.png"

    if not email:
        return RedirectResponse("/auth/login?error=Google+không+có+email")

    # ⭐ Dùng hàm chung – auto tạo user + auto gán role theo domain
    user = get_or_create_social_user(db, email, full_name, avatar)

    # ⭐ Social login → mặc định remember me = True
    create_user_session(request, user, remember_me=True)

    return RedirectResponse("/student/dashboard", status_code=303)


# ======================================================
# MICROSOFT LOGIN (AZURE AD v2)
# ======================================================
MS_REDIRECT_URI = "http://localhost:8000/auth/microsoft/callback"

oauth.register(
    name="microsoft",
    client_id=config("MICROSOFT_CLIENT_ID"),
    client_secret=config("MICROSOFT_CLIENT_SECRET"),
    server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/microsoft")
async def microsoft_login(request: Request):
    """Chuyển hướng đến Microsoft login."""
    return await oauth.microsoft.authorize_redirect(request, MS_REDIRECT_URI)


@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, db: Session = Depends(get_db)):
    """Xử lý callback của Microsoft."""

    token = await oauth.microsoft.authorize_access_token(request)
    info = token.get("userinfo")

    if not info:
        return RedirectResponse("/auth/login?error=Microsoft+Login+Failed")

    # Microsoft có thể trả email hoặc preferred_username
    email = info.get("email") or info.get("preferred_username")
    full_name = info.get("name", "Người dùng Microsoft")
    avatar = "/uploads/avatars/default-avatar.png"

    if not email:
        return RedirectResponse("/auth/login?error=Microsoft+không+có+email")

    # ⭐ Auto create user
    user = get_or_create_social_user(db, email, full_name, avatar)

    # ⭐ Remember Me mặc định
    create_user_session(request, user, remember_me=True)

    return RedirectResponse("/student/dashboard", status_code=303)
