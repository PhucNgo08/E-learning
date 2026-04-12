from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.core.config import get_settings

settings = get_settings()

TRUST_PROXY_HEADERS = False  # Chỉ bật khi có reverse proxy tin cậy
IMPORT_UPLOAD_PATHS = {
    "/admin/exams/import",
}


class SessionExpireMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "session" not in request.scope:
            return await call_next(request)

        session = request.session
        user_id = session.get("user_id")

        # Chưa đăng nhập thì bỏ qua
        if not user_id:
            return await call_next(request)

        path = request.url.path
        method = request.method.upper()
        content_type = (request.headers.get("content-type") or "").lower()
        now_ts = time.time()

        # Các request upload import đặc thù có thể bypass check IP/UA
        is_import_upload = (
            method == "POST"
            and "multipart/form-data" in content_type
            and any(path == allowed or path.endswith(allowed) for allowed in IMPORT_UPLOAD_PATHS)
        )

        # Lấy IP hiện tại
        if TRUST_PROXY_HEADERS:
            xff = request.headers.get("x-forwarded-for", "")
            ip_now = (xff.split(",")[0].strip() if xff else "") or (
                request.client.host if request.client else ""
            )
        else:
            ip_now = request.client.host if request.client else ""

        def unauthorized():
            session.clear()
            if path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Session expired or invalid."},
                    status_code=401,
                )
            return RedirectResponse("/auth/login", status_code=303)

        if not is_import_upload:
            # Check IP
            ip_saved = session.get("session_ip")
            if ip_saved and ip_now and ip_saved != ip_now:
                return unauthorized()

            # Check UA
            ua_saved = session.get("session_ua")
            ua_now = request.headers.get("user-agent", "")
            if ua_saved and ua_now and ua_saved != ua_now:
                return unauthorized()

        # Check absolute expiration
        expires_at_ts = session.get("expires_at_ts")
        if expires_at_ts is not None:
            try:
                if now_ts > float(expires_at_ts):
                    return unauthorized()
            except (TypeError, ValueError):
                return unauthorized()

        # Check inactivity timeout
        last_active = session.get("last_active")
        if last_active is not None:
            try:
                if (now_ts - float(last_active)) > settings.session_max_age_seconds:
                    return unauthorized()
            except (TypeError, ValueError):
                return unauthorized()

        # Gia hạn hoạt động
        session["last_active"] = now_ts

        return await call_next(request)