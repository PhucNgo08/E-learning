"""
==========================================================
🔐 ROUTER: AUTH - RESET PASSWORD (PRO MAX 2025)
Xử lý đặt lại mật khẩu từ link email (token JWT)
==========================================================
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import traceback

# DB + Service
from app.database.connection import get_db
from app.services import user_service

# Template config
from app.config.template_config import get_template_by_path

# Token utils
from app.routers.auth.utils import verify_reset_token


# ============================================================
# 🚀 Khởi tạo Router
# ============================================================
router = APIRouter(prefix="/auth", tags=["Auth - Reset Password"])


# ============================================================
# 🧭 1) TRANG NHẬP MẬT KHẨU MỚI
# ============================================================
@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    """
    Hiển thị form đổi mật khẩu khi người dùng truy cập từ email.
    """
    tpl = get_template_by_path(request.url.path)

    # 🔍 Kiểm tra token hợp lệ
    email = verify_reset_token(token)

    if not email:
        return tpl.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "error": "❌ Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
                "disabled": True,
                "page_title": "🔒 Đặt lại mật khẩu"
            },
            status_code=400
        )

    # Token hợp lệ → Cho nhập mật khẩu mới
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
# 🔐 2) XỬ LÝ ĐẶT LẠI MẬT KHẨU
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
        # 🔍 Kiểm tra token hợp lệ
        email = verify_reset_token(token)
        if not email:
            return tpl.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "error": "❌ Liên kết không hợp lệ hoặc đã hết hạn.",
                    "disabled": True,
                    "page_title": "🔒 Đặt lại mật khẩu"
                },
                status_code=400
            )

        # ⚠️ Kiểm tra nhập lại mật khẩu
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

        # ======================================================
        # ✅ CẬP NHẬT MẬT KHẨU
        # ======================================================
        user_service.update_password(db, email, new_password)
        print(f"✅ Mật khẩu đã được đặt lại cho: {email}")

        # → Điều hướng về login
        return RedirectResponse(url="/auth/login", status_code=303)

    except Exception:
        print("\n❌ Lỗi đặt lại mật khẩu:\n", traceback.format_exc())
        return tpl.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "error": "⚠️ Lỗi hệ thống! Vui lòng thử lại sau.",
                "page_title": "🔒 Đặt lại mật khẩu"
            },
            status_code=500
        )
