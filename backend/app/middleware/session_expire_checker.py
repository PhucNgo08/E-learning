from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from datetime import datetime

SESSION_EXPIRE_MINUTES = 60  # 1 giờ


class SessionExpireMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Nếu không có session (static, file...) → bỏ qua
        if "session" not in request.scope:
            return await call_next(request)

        session = request.session

        user_id = session.get("user_id")
        last_active = session.get("last_active")
        expires_at = session.get("expires_at")
        ip_saved = session.get("session_ip")
        ua_saved = session.get("session_ua")

        now_ts = datetime.utcnow().timestamp()

        # ------------------------------------------------------
        # 1) User chưa login → KHÔNG đụng session
        # ------------------------------------------------------
        if not user_id:
            return await call_next(request)

        # ------------------------------------------------------
        # 2) Không kiểm tra UA/IP cho POST upload/import
        # ------------------------------------------------------
        content_type = request.headers.get("Content-Type", "")

        is_import_post = (
            request.method == "POST"
            and "multipart/form-data" in content_type
        )

        if not is_import_post:
            # Check IP
            if ip_saved and ip_saved != request.client.host:
                session.clear()
                return RedirectResponse("/auth/login")

            # Check User-Agent
            if ua_saved and ua_saved != request.headers.get("User-Agent", ""):
                session.clear()
                return RedirectResponse("/auth/login")

        # ------------------------------------------------------
        # 3) Check expires_at
        # ------------------------------------------------------
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                if datetime.utcnow() > exp_dt:
                    session.clear()
                    return RedirectResponse("/auth/login")
            except Exception:
                session.clear()
                return RedirectResponse("/auth/login")

        # ------------------------------------------------------
        # 4) Check inactivity timeout
        # ------------------------------------------------------
        if last_active and (now_ts - last_active) > SESSION_EXPIRE_MINUTES * 60:
            session.clear()
            return RedirectResponse("/auth/login")

        # ------------------------------------------------------
        # 5) Update last_active SAFE
        # ------------------------------------------------------
        session["last_active"] = now_ts

        # ------------------------------------------------------
        # 6) Continue
        # ------------------------------------------------------
        response = await call_next(request)
        return response
