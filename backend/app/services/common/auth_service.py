"""
==========================================================
👩‍🏫 app/routers/teacher/profile_teacher.py
Quản lý hồ sơ giáo viên (Profile + Avatar + Đổi mật khẩu)
==========================================================
"""
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import shutil
import uuid

from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.services.common.password_service import change_user_password  # ✅ Dùng hàm đổi mật khẩu chung

# =====================================================
# 🚀 KHỞI TẠO ROUTER
# =====================================================
router = APIRouter(
    prefix="/teacher",
    tags=["Teacher - Profile"]
)

# =====================================================
# 📁 TEMPLATE DIR
# =====================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/profile"
)

# =====================================================
# 🖼️ CẤU HÌNH AVATAR
# =====================================================
AVATAR_DIR = Path(r"D:/KhoaHoctructuyen/KHoaHocOnline/backend/app/uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_AVATAR = "/uploads/avatars/default-avatar.png"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# =====================================================
# 📦 HÀM PHỤ: LƯU AVATAR
# =====================================================
def save_avatar_file(file: UploadFile, old_url: str | None = None) -> str:
    """Lưu ảnh đại diện mới và xóa ảnh cũ nếu có"""
    if not file or not file.filename:
        return old_url or DEFAULT_AVATAR

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        print(f"⚠️ File avatar không hợp lệ: {ext}")
        return old_url or DEFAULT_AVATAR

    # Xóa ảnh cũ
    if old_url and old_url != DEFAULT_AVATAR:
        try:
            old_path = Path("D:/KhoaHoctructuyen/KHoaHocOnline/backend") / old_url.lstrip("/")
            if old_path.exists():
                old_path.unlink()
                print(f"🗑️ Đã xóa avatar cũ: {old_path}")
        except Exception as e:
            print(f"⚠️ Không thể xóa avatar cũ: {e}")

    # Lưu ảnh mới
    file_name = f"{uuid.uuid4().hex}{ext}"
    save_path = AVATAR_DIR / file_name
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    print(f"🖼️ Lưu avatar mới: {save_path}")

    return f"/uploads/avatars/{file_name}"

# =====================================================
# 👩‍🏫 TRANG HỒ SƠ GIÁO VIÊN
# =====================================================
@router.get("/profile", response_class=HTMLResponse)
async def teacher_profile(request: Request, db: Session = Depends(get_db)):
    """Hiển thị hồ sơ giáo viên"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    # Lấy danh sách khóa học
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    msg = request.query_params.get("msg")

    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "now": datetime.now(),
            "msg": msg,
        },
    )

# =====================================================
# ✏️ FORM CHỈNH SỬA HỒ SƠ
# =====================================================
@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_form(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    return templates.TemplateResponse("profile_edit.html", {"request": request, "teacher": teacher})

# =====================================================
# 💾 CẬP NHẬT HỒ SƠ
# =====================================================
@router.post("/profile/edit")
async def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    avatar: UploadFile = File(None),
):
    """Cập nhật thông tin và ảnh đại diện"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    # 🖼️ Lưu avatar mới nếu có
    avatar_url = save_avatar_file(avatar, teacher.avatar_url)

    # ✅ Cập nhật thông tin
    teacher.full_name = full_name.strip()
    teacher.email = email.strip()
    teacher.phone = phone.strip()
    teacher.avatar_url = avatar_url
    teacher.updated_at = datetime.utcnow()

    db.commit()
    print(f"✅ Giáo viên {teacher.full_name} cập nhật hồ sơ thành công.")

    return RedirectResponse(url="/teacher/profile?msg=updated", status_code=303)

# =====================================================
# 🔑 FORM ĐỔI MẬT KHẨU
# =====================================================
@router.get("/profile/change-password", response_class=HTMLResponse)
async def change_password_form(request: Request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse("change_password.html", {"request": request})

# =====================================================
# 💾 ĐỔI MẬT KHẨU (DÙNG CHUNG PASSWORD SERVICE)
# =====================================================
@router.post("/profile/change-password")
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Đổi mật khẩu cho giáo viên đang đăng nhập"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    # 🔁 Gọi service dùng chung
    result = change_user_password(db, user_id, current_password, new_password, confirm_password)
    if not result["success"]:
        return HTMLResponse(
            f"<h3 class='text-danger text-center mt-5'>{result['message']}</h3>", status_code=400
        )

    print(f"🔑 Giáo viên ID={user_id} đổi mật khẩu thành công.")
    return RedirectResponse(url="/teacher/profile?msg=password_changed", status_code=303)
