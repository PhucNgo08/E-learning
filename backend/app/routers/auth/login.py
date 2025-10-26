"""
==========================================================
🔐 ROUTER: AUTH - LOGIN
Xử lý đăng nhập người dùng (Admin / Teacher / Student)
==========================================================
"""

import hashlib
import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

# ✅ Import database & service
from app.database.connection import get_db
from app.models.user import User
from app.services.common.password_service import verify_password

# ✅ Import cấu hình template
from app.config.template_config import templates

# ==========================================================
# ⚙️ Cấu hình Router & Logger
# ==========================================================
login_router = APIRouter(prefix="/auth", tags=["Auth - Login"])
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ==========================================================
# 🧩 HÀM XÁC THỰC NGƯỜI DÙNG
# ==========================================================
def authenticate_user(db: Session, username: str, password: str):
    """
    ✅ Xác thực người dùng:
    - Hỗ trợ hash cũ SHA256 và hash mới bcrypt
    - Trả về đối tượng User nếu đúng, hoặc "username"/"password" nếu sai
    """
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return "username"

        hashed_pw = user.password_hash or ""
        if hashed_pw.startswith("$2b$") or hashed_pw.startswith("$2a$"):
            valid = verify_password(password, hashed_pw)
        else:
            valid = hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed_pw

        if not valid:
            return "password"

        return user

    except Exception as e:
        logger.error(f"💥 Lỗi xác thực người dùng: {e}")
        traceback.print_exc()
        return None


# ==========================================================
# 📄 GET /auth/login — Hiển thị form đăng nhập
# ==========================================================
@login_router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: Optional[str] = None):
    """
    Hiển thị form đăng nhập.
    Nếu người dùng đã có session hợp lệ → chuyển hướng đến dashboard.
    """
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    # ✅ Nếu đã đăng nhập rồi, chuyển đến dashboard tương ứng
    if user_id and role:
        if role == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        elif role == "teacher":
            return RedirectResponse(url="/teacher/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        elif role == "student":
            return RedirectResponse(url="/student/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    # 🧩 Nếu chưa login thì hiển thị form đăng nhập
    return templates["auth"].TemplateResponse(
        "login.html",
        {"request": request, "error": error},
    )


# ==========================================================
# 🔑 POST /auth/login — Xử lý đăng nhập
# ==========================================================
@login_router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Xử lý đăng nhập:
    - Kiểm tra username/password
    - Lưu session: user_id, username, role
    - Chuyển hướng đến dashboard phù hợp
    """
    logger.info(f"🔐 Đăng nhập: {username}")

    auth_result = authenticate_user(db, username, password)

    # ❌ Sai username
    if auth_result == "username":
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "Tên đăng nhập không tồn tại."},
        )

    # ❌ Sai mật khẩu
    if auth_result == "password":
        return templates["auth"].TemplateResponse(
            "login.html",
            {"request": request, "error": "Mật khẩu không đúng."},
        )

    # ✅ Đăng nhập thành công
    if isinstance(auth_result, User):
        user = auth_result

        # Xóa session cũ
        request.session.clear()

        # 🧠 Ghi session mới
        request.session["user_id"] = str(user.id)
        request.session["username"] = user.username
        request.session["role"] = (
            user.role.value if hasattr(user.role, "value") else str(user.role)
        )

        logger.info(f"🎯 Session mới: {dict(request.session)}")

        # 🚀 Điều hướng theo vai trò
        role = request.session.get("role")
        if role == "admin":
            redirect_url = "/admin/dashboard"
        elif role == "teacher":
            redirect_url = "/teacher/dashboard"
        elif role == "student":
            redirect_url = "/student/dashboard"
        else:
            redirect_url = "/"

        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    # 💥 Lỗi không xác định
    return templates["auth"].TemplateResponse(
        "login.html",
        {"request": request, "error": "Đã xảy ra lỗi không xác định. Vui lòng thử lại."},
    )


# ==========================================================
# 🚪 GET /auth/logout — Đăng xuất
# ==========================================================
@login_router.get("/logout")
async def logout(request: Request):
    """Xóa session và đưa người dùng về trang đăng nhập"""
    username = request.session.get("username", "Unknown")
    logger.info(f"🚪 Đăng xuất: {username}")

    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
