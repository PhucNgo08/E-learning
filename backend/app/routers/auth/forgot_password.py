"""
==========================================================
🔐 ROUTER: AUTH - FORGOT PASSWORD
Xử lý chức năng quên mật khẩu & gửi email đặt lại
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import traceback

# ✅ Import cấu hình template
from app.config.template_config import get_template_by_path
# ✅ Import database
from app.database.connection import get_db
# ✅ Import service đúng cách
from app.services import user_service
# ✅ Import tiện ích gửi mail và token reset
from app.routers.auth.utils import send_reset_email, generate_reset_token


# ============================================================
# 🚀 Router khởi tạo
# ============================================================
router = APIRouter(prefix="/auth", tags=["Auth - Forgot Password"])


# ============================================================
# 🧭 1️⃣ Trang nhập email khôi phục mật khẩu
# ============================================================
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """
    Hiển thị form nhập email để khôi phục mật khẩu.
    """
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "forgot_password.html",
        {"request": request, "page_title": "🔑 Quên mật khẩu"}
    )


# ============================================================
# ✉️ 2️⃣ Gửi email khôi phục mật khẩu
# ============================================================
@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Xử lý gửi email đặt lại mật khẩu.
    """
    tpl = get_template_by_path(request.url.path)

    try:
        # 🔍 Kiểm tra email có tồn tại trong hệ thống
        user = user_service.get_user_by_email(email, db)  # ✅ Gọi đúng service
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

        # 🪄 Sinh token + link reset
        token = generate_reset_token(email)
        reset_link = f"http://localhost:8000/auth/reset-password?token={token}"

        # ✉️ Gửi email
        send_reset_email(email, reset_link)
        print(f"📧 Gửi mail đặt lại mật khẩu cho {email}: {reset_link}")

        return tpl.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "message": "✅ Hướng dẫn đặt lại mật khẩu đã được gửi qua email.",
                "page_title": "🔑 Quên mật khẩu"
            }
        )

    except Exception:
        print("\n❌ Lỗi xử lý quên mật khẩu:\n", traceback.format_exc())
        return tpl.TemplateResponse(
            "forgot_password.html",
            {
                "request": request,
                "error": "⚠️ Có lỗi xảy ra, vui lòng thử lại sau.",
                "page_title": "🔑 Quên mật khẩu"
            },
            status_code=500
        )
