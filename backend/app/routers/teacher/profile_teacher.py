from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
from passlib.context import CryptContext

from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course

# ==============================
# 🚀 Khởi tạo router
# ==============================
router = APIRouter(
    prefix="/teacher",
    tags=["Teacher - Profile"]
)

# ==============================
# 📁 Cấu hình template
# ==============================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/profile"
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==============================
# 👩‍🏫 Trang hồ sơ giáo viên
# ==============================
@router.get("/profile", response_class=HTMLResponse)
async def teacher_profile(request: Request, db: Session = Depends(get_db)):
    """Hiển thị thông tin hồ sơ giáo viên hiện tại"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    # ✅ Kiểm tra session
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    # Lấy danh sách khóa học của giáo viên
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "now": datetime.now()
        }
    )


# ==============================
# ✏️ Trang chỉnh sửa hồ sơ (GET)
# ==============================
@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_form(request: Request, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa hồ sơ giáo viên"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    return templates.TemplateResponse(
        "profile_edit.html",
        {"request": request, "teacher": teacher, "now": datetime.now()}
    )


# ==============================
# 💾 Xử lý cập nhật hồ sơ (POST)
# ==============================
@router.post("/profile/edit")
async def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
):
    """Cập nhật thông tin hồ sơ"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    # ✅ Cập nhật thông tin
    teacher.full_name = full_name
    teacher.email = email
    teacher.phone = phone
    teacher.updated_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/teacher/profile", status_code=303)


# ==============================
# 🔑 Trang đổi mật khẩu (GET)
# ==============================
@router.get("/profile/change-password", response_class=HTMLResponse)
async def change_password_form(request: Request):
    """Hiển thị form đổi mật khẩu"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates.TemplateResponse(
        "change_password.html",
        {"request": request}
    )


# ==============================
# 💾 Xử lý đổi mật khẩu (POST)
# ==============================
@router.post("/profile/change-password")
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Xử lý đổi mật khẩu cá nhân"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy tài khoản.</h3>", status_code=404)

    # ✅ Kiểm tra mật khẩu cũ
    try:
        if not pwd_context.verify(current_password, teacher.password_hash):
            return HTMLResponse("<h3 class='text-danger text-center mt-5'>❌ Mật khẩu hiện tại không đúng.</h3>", status_code=400)
    except Exception:
        return HTMLResponse("<h3 class='text-danger text-center mt-5'>⚠️ Mật khẩu trong hệ thống chưa được mã hóa đúng chuẩn. Hãy liên hệ quản trị viên.</h3>", status_code=400)

    # ✅ Kiểm tra mật khẩu mới
    if new_password != confirm_password:
        return HTMLResponse("<h3 class='text-danger text-center mt-5'>❌ Mật khẩu xác nhận không khớp.</h3>", status_code=400)

    # ✅ Cập nhật mật khẩu mới
    teacher.password_hash = pwd_context.hash(new_password)
    teacher.updated_at = datetime.utcnow()
    db.commit()

    # ✅ Hiển thị thông báo thành công
    return RedirectResponse(url="/teacher/profile", status_code=303)
