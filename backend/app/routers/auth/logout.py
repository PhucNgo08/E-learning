from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.services.common.auth_service import logout_user

logout_router = APIRouter(prefix="/auth", tags=["Auth - Logout"])

logger = logging.getLogger("auth_logout")
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


@logout_router.get("/logout")
async def logout(request: Request):
    username = request.session.get("username") or request.session.get("email") or "unknown"

    try:
        logout_user(request)
        logger.info("User '%s' logged out successfully", username)
    except Exception as exc:
        logger.exception("Logout failed for user '%s': %s", username, exc)

        if wants_json(request):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Đăng xuất thất bại.",
                },
            )

        return RedirectResponse(url="/auth/login?error=logout_failed", status_code=303)

    if wants_json(request):
        return JSONResponse(
            {
                "success": True,
                "message": "Đăng xuất thành công.",
                "redirect_to": "/auth/login",
            }
        )

    return RedirectResponse(url="/auth/login", status_code=303)