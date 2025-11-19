"""
==========================================================
🔵 SOCIAL LOGIN ROUTER — PRO MAX v4.0 (Google + Microsoft)
✔ PKCE + Email Verification
✔ Auto-create user + auto role mapping
✔ Secure session + remember me
✔ Dynamic redirect by role
✔ Avatar fallback (Google/Microsoft/Gravatar)
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from decouple import config
import hashlib

from app.database.connection import get_db
from app.services.common.auth_service import (
    create_user_session,
    get_or_create_social_user,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth - Social Login"])

oauth = OAuth()

# ======================================================
# 🔧 DOMAIN CONFIG
# ======================================================
DOMAIN = config("DOMAIN", default="http://localhost:8000")

GOOGLE_REDIRECT_URI = f"{DOMAIN}/auth/google/callback"
MS_REDIRECT_URI      = f"{DOMAIN}/auth/microsoft/callback"

# ======================================================
# 🔵 GOOGLE LOGIN
# ======================================================
oauth.register(
    name="google",
    client_id=config("GOOGLE_CLIENT_ID"),
    client_secret=config("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
    pkce=True,
)


@router.get("/google")
async def google_login(request: Request):
    """Chuyển đến Google (OAuth2 + PKCE)."""
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Xử lý callback của Google."""

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/auth/login?error=Google+Login+Failed", 303)

    info = token.get("userinfo")
    if not info:
        return RedirectResponse("/auth/login?error=Google+không+có+userinfo", 303)

    # Google verify
    if not info.get("email_verified", True):
        return RedirectResponse("/auth/login?error=Email+chưa+xác+thực", 303)

    email = info["email"].lower()
    full_name = info.get("name", "Google User")
    avatar = info.get("picture") or "/uploads/avatars/default-avatar.png"

    # ⭐ Auto create or find user
    user: User = get_or_create_social_user(db, email, full_name, avatar)

    # ⭐ Create session
    create_user_session(request, user, remember_me=True)

    return RedirectResponse(f"/{user.role}/dashboard", 303)


# ======================================================
# 🟣 MICROSOFT LOGIN (Azure AD v2)
# ======================================================
oauth.register(
    name="microsoft",
    client_id=config("MICROSOFT_CLIENT_ID"),
    client_secret=config("MICROSOFT_CLIENT_SECRET"),
    server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
    pkce=True,
)


@router.get("/microsoft")
async def microsoft_login(request: Request):
    """Chuyển đến Microsoft Login."""
    return await oauth.microsoft.authorize_redirect(request, MS_REDIRECT_URI)


@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, db: Session = Depends(get_db)):

    try:
        token = await oauth.microsoft.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/auth/login?error=Microsoft+Login+Failed", 303)

    info = token.get("userinfo")
    if not info:
        return RedirectResponse("/auth/login?error=Microsoft+không+có+userinfo", 303)

    # Microsoft trả email khác với Google
    email = info.get("email") or info.get("preferred_username")
    if not email:
        return RedirectResponse("/auth/login?error=Không+có+email", 303)

    email = email.lower()
    full_name = info.get("name", "Microsoft User")

    # ⭐ Microsoft không trả avatar → dùng Gravatar
    gravatar_hash = hashlib.md5(email.encode()).hexdigest()
    avatar = f"https://www.gravatar.com/avatar/{gravatar_hash}?d=identicon"

    # ⭐ Create or get user
    user: User = get_or_create_social_user(db, email, full_name, avatar)

    # ⭐ Create session
    create_user_session(request, user, remember_me=True)

    return RedirectResponse(f"/{user.role}/dashboard", 303)
