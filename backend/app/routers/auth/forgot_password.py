"""
==========================================================
🔐 ROUTER: AUTH - FORGOT PASSWORD (PRO MAX 2025)
• Nhập email
• Gửi mail reset password
• Hiển thị link reset trực tiếp để test nhanh (LOCALHOST)
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import traceback

# Templates
from app.config.template_config import get_template_by_path

# Database
from app.database.connection import get_db

# Service lấy user
from app.services import user_service

# Mail + Token utils
from app.routers.auth.utils import (
    send_reset_email,
    generate_reset_token
)


# ============================================================
# 🚀 Router khởi tạo
# ============================================================
router = APIRouter(prefix="/auth", tags=["Auth - Forgot Password"])


# ============================================================
# 🧭 1) Trang nhập email khôi phục mật khẩu
# ============================================================
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    tpl = get_template_by_path(request.url.path)

    return tpl.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "page_title": "🔑 Quên mật khẩu"
        }
    )


# ============================================================
# ✉️ 2) Gửi email + trả link reset trực tiếp
# ============================================================
@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    tpl = get_template_by_path(request.url.path)

    try:
        # ------------------------------------------------------
        # 🔍 Kiểm tra email có tồn tại?
        # ------------------------------------------------------
        user = user_service.get_user_by_email(email, db)

        if not user:
            return tpl.TemplateResponse(
                "forgot_password.html",
                {
                    "request": request,
                    "error": "❌ Email không tồn tại trong hệ thống.",
                    "page_title": "🔑 Quên mật khẩu"
                },
                status_code=400
            )

        # ------------------------------------------------------
        # 🔐 Tạo token reset mật khẩu
        # ------------------------------------------------------
        token = generate_reset_token(email)

        # ------------------------------------------------------
        # 🔗 Tạo link đặt lại mật khẩu (Click trực tiếp)
        # ------------------------------------------------------
        reset_link = f"http://localhost:8000/auth/reset-password?token={token}"

        # ------------------------------------------------------
        # ✉️ Gửi email (kèm link)
        # ------------------------------------------------------
        send_reset_email(email, reset_link)

        print(f"📧 Reset link gửi tới {email}: {reset_link}")

        # ------------------------------------------------------
        # 🟦 Trả link trực tiếp để test nhanh
        # ------------------------------------------------------
        return tpl.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "message": "📩 Đã gửi hướng dẫn đặt lại mật khẩu.",
                "reset_link": reset_link,   # ⭐ Chỗ này để HTML hiển thị link
                "page_title": "🔑 Quên mật khẩu"
            }
        )

    except Exception:
        print("\n❌ Lỗi xử lý forgot-password:\n", traceback.format_exc())
        return tpl.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "error": "⚠️ Có lỗi xảy ra, vui lòng thử lại.",
                "page_title": "🔑 Quên mật khẩu"
            },
            status_code=500
        )
