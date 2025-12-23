from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from datetime import datetime

SESSION_EXPIRE_MINUTES = 60  # 1 giờ


class SessionExpireMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Không có session scope -> bỏ qua
        if "session" not in request.scope:
            return await call_next(request)

        session = request.session

        user_id = session.get("user_id")
        last_active = session.get("last_active")
        expires_at = session.get("expires_at")
        ip_saved = session.get("session_ip")
        ua_saved = session.get("session_ua")

        now_ts = datetime.utcnow().timestamp()

        # 1) Chưa login -> không đụng session
        if not user_id:
            return await call_next(request)

        # Helper: lấy IP thực (nếu dùng reverse proxy)
        xff = request.headers.get("x-forwarded-for", "")
        ip_now = (xff.split(",")[0].strip() if xff else None) or (request.client.host if request.client else "")

        # 2) Chỉ bypass UA/IP cho đúng import upload (đừng bypass mọi multipart)
        content_type = request.headers.get("Content-Type", "")
        path = request.url.path

        is_import_upload = (
            request.method == "POST"
            and "multipart/form-data" in content_type
            and "/admin/exams/" in path
            and path.endswith("/import")
        )

        if not is_import_upload:
            # Check IP
            if ip_saved and ip_saved != ip_now:
                session.clear()
                return RedirectResponse("/auth/login", status_code=303)

            # Check User-Agent
            ua_now = request.headers.get("User-Agent", "")
            if ua_saved and ua_saved != ua_now:
                session.clear()
                return RedirectResponse("/auth/login", status_code=303)

        # 3) Check expires_at (so sánh timestamp để tránh lỗi timezone-aware)
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                exp_ts = exp_dt.timestamp()
                if now_ts > exp_ts:
                    session.clear()
                    return RedirectResponse("/auth/login", status_code=303)
            except Exception:
                # Nếu parse lỗi thì đừng logout “oan” ngay, bạn có thể chọn:
                # A) clear session như cũ (an toàn)
                # B) bỏ qua expires_at (đỡ logout oan)
                session.clear()
                return RedirectResponse("/auth/login", status_code=303)

        # 4) Check inactivity timeout
        if last_active and (now_ts - float(last_active)) > SESSION_EXPIRE_MINUTES * 60:
            session.clear()
            return RedirectResponse("/auth/login", status_code=303)

        # 5) Update last_active
        session["last_active"] = now_ts

        # 6) Continue
        return await call_next(request)
