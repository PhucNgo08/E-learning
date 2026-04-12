from __future__ import annotations

import hashlib

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.connection import get_db
from app.services.common.auth_service import (
    build_dashboard_redirect,
    create_user_session,
    get_or_create_social_user,
    normalize_role_code,
)

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Auth - Social Login"])
oauth = OAuth()

DOMAIN = "http://localhost:8000"
GOOGLE_REDIRECT_URI = f"{DOMAIN}/auth/google/callback"
MS_REDIRECT_URI = f"{DOMAIN}/auth/microsoft/callback"

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
        pkce=True,
    )

if settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET:
    oauth.register(
        name="microsoft",
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
        pkce=True,
    )


@router.get("/google")
async def google_login(request: Request):
    if not getattr(oauth, "google", None):
        return RedirectResponse("/auth/login?error=Google+OAuth+chưa+được+cấu+hình", status_code=303)
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not getattr(oauth, "google", None):
        return RedirectResponse("/auth/login?error=Google+OAuth+chưa+được+cấu+hình", status_code=303)

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/auth/login?error=Google+Login+Failed", status_code=303)

    info = token.get("userinfo") or {}
    if not info:
        return RedirectResponse("/auth/login?error=Google+không+có+userinfo", status_code=303)

    if not info.get("email_verified", True):
        return RedirectResponse("/auth/login?error=Email+chưa+xác+thực", status_code=303)

    email = (info.get("email") or "").strip().lower()
    if not email:
        return RedirectResponse("/auth/login?error=Không+có+email", status_code=303)

    full_name = (info.get("name") or "Google User").strip()
    avatar = info.get("picture") or "/uploads/avatars/default-avatar.png"

    user = get_or_create_social_user(
        db,
        email=email,
        full_name=full_name,
        avatar=avatar,
    )

    role_value = getattr(user, "resolved_role", None) or "student"

    create_user_session(request, db, user, remember_me=True)
    return RedirectResponse(build_dashboard_redirect(role_value), status_code=303)


@router.get("/microsoft")
async def microsoft_login(request: Request):
    if not getattr(oauth, "microsoft", None):
        return RedirectResponse("/auth/login?error=Microsoft+OAuth+chưa+được+cấu+hình", status_code=303)
    return await oauth.microsoft.authorize_redirect(request, MS_REDIRECT_URI)


@router.get("/microsoft/callback")
async def microsoft_callback(request: Request, db: Session = Depends(get_db)):
    if not getattr(oauth, "microsoft", None):
        return RedirectResponse("/auth/login?error=Microsoft+OAuth+chưa+được+cấu+hình", status_code=303)

    try:
        token = await oauth.microsoft.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/auth/login?error=Microsoft+Login+Failed", status_code=303)

    info = token.get("userinfo") or {}
    if not info:
        return RedirectResponse("/auth/login?error=Microsoft+không+có+userinfo", status_code=303)

    email = (info.get("email") or info.get("preferred_username") or "").strip().lower()
    if not email:
        return RedirectResponse("/auth/login?error=Không+có+email", status_code=303)

    full_name = (info.get("name") or "Microsoft User").strip()
    gravatar_hash = hashlib.md5(email.encode()).hexdigest()
    avatar = f"https://www.gravatar.com/avatar/{gravatar_hash}?d=identicon"

    user = get_or_create_social_user(
        db,
        email=email,
        full_name=full_name,
        avatar=avatar,
    )

    role_value = getattr(user, "resolved_role", None) or "student"

    create_user_session(request, db, user, remember_me=True)
    return RedirectResponse(build_dashboard_redirect(role_value), status_code=303)