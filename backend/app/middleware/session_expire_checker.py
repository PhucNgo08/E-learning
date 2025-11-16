from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from datetime import datetime

SESSION_EXPIRE_MINUTES = 60  # 1 giờ

class SessionExpireMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Nếu session middleware chưa inject → KHÔNG BAO GIỜ ĐƯỢC DÙNG request.session trực tiếp
        if "session" not in request.scope:
            return await call_next(request)

        session = request.session

        # Kiểm tra xem có người dùng đã đăng nhập không
        user_id = session.get("user_id")
        
        # Nếu chưa đăng nhập, không cần xử lý gì thêm
        if not user_id:
            return await call_next(request)

        # Lấy last activity
        last_active = session.get("last_active")

        now_ts = datetime.utcnow().timestamp()

        # Kiểm tra session đã hết hạn
        if last_active and now_ts - last_active > SESSION_EXPIRE_MINUTES * 60:
            session.clear()  # Xóa session nếu hết hạn
            return RedirectResponse("/auth/login")

        # Cập nhật thời gian hoạt động của session
        session["last_active"] = now_ts

        return await call_next(request)
