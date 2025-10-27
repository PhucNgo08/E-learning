from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.routers.auth.utils import verify_reset_token
from app.services import user_service
from app.config.template_config import get_template_by_path
import traceback

# ============================================================
# 🚀 Khởi tạo Router
# ============================================================
router = APIRouter(prefix="/auth", tags=["Auth - Reset Password"])

# ============================================================
# 🧭 1️⃣ Trang nhập mật khẩu mới
# ============================================================
@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_form(request: Request, token: str):
    """Hiển thị form đổi mật khẩu khi người dùng truy cập từ email"""
    tpl = get_template_by_path(request.url.path)

    email = verify_reset_token(token)
    if not email:
        return tpl.TemplateResponse(
            "auth/reset_password.html",
            {
                "request": request,
                "error": "❌ Liên kết không hợp lệ hoặc đã hết hạn.",
                "disabled": True
            }
        )

    return tpl.TemplateResponse(
        "auth/reset_password.html",
        {"request": request, "token": token, "email": email}
    )

# ============================================================
# 🔐 2️⃣ Xử lý đặt lại mật khẩu
# ============================================================
@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Xử lý đổi mật khẩu từ form"""
    tpl = get_template_by_path(request.url.path)

    try:
        email = verify_reset_token(token)
        if not email:
            return tpl.TemplateResponse(
                "auth/reset_password.html",
                {
                    "request": request,
                    "error": "❌ Liên kết đã hết hạn hoặc không hợp lệ.",
                    "disabled": True
                }
            )

        if new_password != confirm_password:
            return tpl.TemplateResponse(
                "auth/reset_password.html",
                {
                    "request": request,
                    "token": token,
                    "email": email,
                    "error": "⚠️ Mật khẩu xác nhận không trùng khớp!"
                }
            )

        # ✅ Cập nhật mật khẩu
        user_service.update_password(db, email, new_password)

        print(f"✅ Đặt lại mật khẩu thành công cho {email}")
        return RedirectResponse(url="/auth/login", status_code=303)

    except Exception:
        print("\n❌ Lỗi đặt lại mật khẩu:\n", traceback.format_exc())
        return tpl.TemplateResponse(
            "auth/reset_password.html",
            {
                "request": request,
                "error": "❌ Lỗi hệ thống, vui lòng thử lại sau."
            },
            status_code=500
        )
