"""
==========================================================
🔐 ROUTER: AUTH - RESET PASSWORD
Xử lý đặt lại mật khẩu từ link email (token JWT)
==========================================================
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import traceback

# ✅ Import service, DB & template
from app.database.connection import get_db
from app.services import user_service
from app.config.template_config import get_template_by_path
from app.routers.auth.utils import verify_reset_token

# ============================================================
# 🚀 Khởi tạo Router
# ============================================================
router = APIRouter(prefix="/auth", tags=["Auth - Reset Password"])

# ============================================================
# 🧭 1️⃣ Trang nhập mật khẩu mới
# ============================================================
@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    """
    Hiển thị form đổi mật khẩu khi người dùng truy cập từ email.
    """
    tpl = get_template_by_path(request.url.path)

    # ✅ Kiểm tra token hợp lệ
    email = verify_reset_token(token)
    if not email:
        return tpl.TemplateResponse(
            "reset_password.html",   # ⚠️ Không cần "auth/" nếu template_config tự map
            {
                "request": request,
                "error": "❌ Liên kết không hợp lệ hoặc đã hết hạn.",
                "disabled": True,
                "page_title": "🔒 Đặt lại mật khẩu"
            },
            status_code=400
        )

    return tpl.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "token": token,
            "email": email,
            "page_title": "🔒 Đặt lại mật khẩu"
        }
    )


# ============================================================
# 🔐 2️⃣ Xử lý đặt lại mật khẩu
# ============================================================
@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Xử lý form đổi mật khẩu từ người dùng.
    """
    tpl = get_template_by_path(request.url.path)

    try:
        # 🔍 Xác thực token
        email = verify_reset_token(token)
        if not email:
            return tpl.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "error": "❌ Liên kết đã hết hạn hoặc không hợp lệ.",
                    "disabled": True,
                    "page_title": "🔒 Đặt lại mật khẩu"
                },
                status_code=400
            )

        # ⚠️ Kiểm tra mật khẩu nhập lại
        if new_password != confirm_password:
            return tpl.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "token": token,
                    "email": email,
                    "error": "⚠️ Mật khẩu xác nhận không trùng khớp!",
                    "page_title": "🔒 Đặt lại mật khẩu"
                },
                status_code=400
            )

        # ✅ Cập nhật mật khẩu trong DB
        user_service.update_password(db, email, new_password)
        print(f"✅ Đặt lại mật khẩu thành công cho {email}")

        # ➡️ Chuyển hướng về trang đăng nhập
        return RedirectResponse(url="/auth/login", status_code=303)

    except Exception:
        print("\n❌ Lỗi đặt lại mật khẩu:\n", traceback.format_exc())
        return tpl.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "error": "⚠️ Lỗi hệ thống, vui lòng thử lại sau.",
                "page_title": "🔒 Đặt lại mật khẩu"
            },
            status_code=500
        )
