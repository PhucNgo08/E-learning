from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.services.common.auth_service import (
    authenticate_user,
    build_dashboard_redirect,
    create_user_session,
)
from app.services.wallet_service import create_wallet, get_wallet

login_router = APIRouter(prefix="/auth", tags=["Auth - Login"])

logger = logging.getLogger("auth_login")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def wants_json(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    content_type = (request.headers.get("content-type") or "").lower()
    requested_with = (request.headers.get("x-requested-with") or "").lower()

    return (
        request.url.path.startswith("/api")
        or "application/json" in accept
        or "application/json" in content_type
        or requested_with == "xmlhttprequest"
    )


async def read_login_payload(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            payload = await request.json()
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    try:
        form = await request.form()
        return dict(form)
    except Exception:
        return {}


def to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "on", "yes", "y"}


def render_login_error(request: Request, message: str, status_code: int = 400):
    if wants_json(request):
        return JSONResponse(
            status_code=status_code,
            content={"success": False, "message": message},
        )

    return templates["auth"].TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": message,
        },
        status_code=status_code,
    )


@login_router.get("/login", response_class=HTMLResponse)
async def show_login(request: Request, error: str | None = None):
    # Nếu còn session cũ thì xóa để luôn hiện trang đăng nhập
    # Tránh lỗi chạy lại chương trình rồi bấm đăng nhập bị nhảy vào trang cũ
    if request.session.get("user_id") or request.session.get("role") or request.session.get("user_role"):
        request.session.clear()

    return templates["auth"].TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
        },
    )


@login_router.post("/login")
async def do_login(request: Request, db: Session = Depends(get_db)):
    payload = await read_login_payload(request)

    login_id = (
        payload.get("identifier")
        or payload.get("username")
        or payload.get("email")
        or ""
    )
    password = payload.get("password") or ""
    remember_me = to_bool(payload.get("remember_me"))

    login_id = str(login_id).strip()
    password = str(password).strip()

    if not login_id:
        return render_login_error(request, "❌ Vui lòng nhập email hoặc username.")

    if not password:
        return render_login_error(request, "❌ Vui lòng nhập mật khẩu.")

    result = authenticate_user(db, login_id, password)
    if not result.get("success"):
        return render_login_error(
            request,
            result.get("message") or "Đăng nhập thất bại.",
            status_code=401,
        )

    user = result["user"]

    # Tạo ví tự động cho student nếu chưa có
    role_value = getattr(user, "resolved_role", None) or ""
    if role_value == "student":
        wallet = get_wallet(db, user.id)
        if not wallet:
            create_wallet(db, user.id)

    create_user_session(request, db, user, remember_me=remember_me)

    # Lấy role sau khi session đã tạo xong
    role_value = request.session.get("role") or getattr(user, "resolved_role", None) or "student"
    redirect_to = build_dashboard_redirect(role_value)

    logger.info(
        "User '%s' logged in successfully with role='%s'",
        user.username,
        role_value,
    )

    if wants_json(request):
        return JSONResponse(
            {
                "success": True,
                "message": "Đăng nhập thành công.",
                "redirect_to": redirect_to,
                "role": role_value,
                "remember_me": remember_me,
            }
        )

    return RedirectResponse(redirect_to, status_code=303)