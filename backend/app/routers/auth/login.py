import traceback
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.services.common.password_service import verify_password


# ==============================
# ⚙️ Cấu hình router & template
# ==============================
login_router = APIRouter(prefix="/auth", tags=["Auth"])

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/auth"
)

# ==============================
# 🧠 Logger
# ==============================
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================
# 🔐 Hàm xác thực người dùng
# ============================================================
def authenticate_user(db: Session, username: str, password: str):
    """
    ✅ Xác thực người dùng theo username & password.
    - Hỗ trợ hash cũ (SHA256) và hash mới (bcrypt).
    - Trả về đối tượng User nếu thành công, hoặc "username"/"password" nếu thất bại.
    """
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning(f"❌ Không tồn tại tài khoản: {username}")
            return "username"

        hashed_pw = user.password_hash or ""

        # Xác định loại hash
        if hashed_pw.startswith("$2b$") or hashed_pw.startswith("$2a$"):
            valid = verify_password(password, hashed_pw)
        else:
            # hash cũ SHA256
            sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            valid = sha256_hash == hashed_pw

        if not valid:
            logger.warning(f"⚠️ Sai mật khẩu cho tài khoản: {username}")
            return "password"

        return user

    except Exception as e:
        logger.error(f"💥 Lỗi xác thực người dùng: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Lỗi máy chủ trong quá trình xác thực")

# ============================================================
# 📄 GET /auth/login – Hiển thị form đăng nhập
# ============================================================
@login_router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request, error: Optional[str] = None):
    """
    Hiển thị form đăng nhập.
    Nếu người dùng đã đăng nhập → chuyển hướng đến dashboard tương ứng.
    """
    session_role = request.session.get("role")

    if session_role == "admin":
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    elif session_role == "teacher":
        return RedirectResponse(url="/teacher/dashboard", status_code=303)
    elif session_role == "student":
        return RedirectResponse(url="/student/dashboard", status_code=303)

    return templates.TemplateResponse("login.html", {"request": request, "error": error})

# ============================================================
# 🔑 POST /auth/login – Xử lý đăng nhập
# ============================================================
@login_router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Xử lý đăng nhập:
    - Kiểm tra username/password.
    - Lưu session: user_id, username, role.
    - Chuyển hướng theo vai trò.
    """
    logger.info(f"🧩 Đang đăng nhập tài khoản: {username}")

    auth_result = authenticate_user(db, username, password)

    # ❌ Sai username
    if auth_result == "username":
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Tên đăng nhập không tồn tại."},
        )

    # ❌ Sai mật khẩu
    if auth_result == "password":
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Mật khẩu không đúng."},
        )

    # ✅ Đăng nhập thành công
    if isinstance(auth_result, User):
        user = auth_result
        logger.info(f"✅ Đăng nhập thành công: {user.username} (role: {user.role})")

        # Xóa session cũ để tránh lưu chồng
        request.session.clear()

        # 🧠 Lưu session mới
        request.session["user_id"] = str(user.id)
        request.session["username"] = user.username

        # Nếu role là Enum -> lấy value, nếu là string -> giữ nguyên
        if hasattr(user.role, "value"):
            request.session["role"] = user.role.value
        else:
            request.session["role"] = str(user.role)

        logger.info(f"🎯 Session mới: {request.session}")

        # 🔀 Điều hướng theo vai trò
        role = request.session["role"]
        if role == "admin":
            redirect_url = "/admin/dashboard"
        elif role == "teacher":
            redirect_url = "/teacher/dashboard"
        elif role == "student":
            redirect_url = "/student/dashboard"
        else:
            redirect_url = "/"

        return RedirectResponse(url=redirect_url, status_code=303)

    # 💥 Lỗi không xác định
    logger.error("💥 Lỗi không xác định khi đăng nhập.")
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Đã xảy ra lỗi không xác định. Vui lòng thử lại."},
    )

# ============================================================
# 🚪 GET /auth/logout – Đăng xuất
# ============================================================
@login_router.get("/logout")
async def logout(request: Request):
    """
    Xóa toàn bộ session và đưa người dùng về trang đăng nhập.
    """
    username = request.session.get("username", "Unknown")
    logger.info(f"🚪 Đăng xuất người dùng: {username}")

    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
