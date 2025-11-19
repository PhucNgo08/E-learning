"""
==========================================================
🎓 ROUTER: Student - Profile (PRODUCTION 2025 - FINAL)
Quản lý hồ sơ cá nhân, avatar, password
Tối ưu bảo mật – tốc độ – sạch – không rác
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, UploadFile, File, Form
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid, os, traceback
from PIL import Image
from io import BytesIO

# Database & templates
from app.database.connection import get_db
from app.config.template_config import templates

# Models
from app.models.user import User
from app.models.lesson_progress import LessonProgress
from app.models.quiz_attempt import QuizAttempt
from app.models.assignment_submission import AssignmentSubmission
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.models.security_setting import SecuritySettings

# Services
from app.services.common.password_service import change_user_password

# Upload folder
from app.config.paths import UPLOAD_AVATARS


# =====================================================
# ⚙️ Router init
# =====================================================
router = APIRouter(
    prefix="/student/profile",
    tags=["Student - Profile"]
)


# =====================================================
# 🧩 Helper Functions
# =====================================================

def resize_image(image_bytes: bytes, size=(512, 512)) -> bytes:
    """Resize ảnh về 512x512 để tối ưu sidebar & storage."""
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = image.resize(size, Image.LANCZOS)

    output = BytesIO()
    image.save(output, format="JPEG", quality=92)
    return output.getvalue()


def delete_old_avatar(path: str):
    """Xoá avatar cũ (trừ avatar mặc định)."""
    try:
        if path and "default-avatar.png" not in path:
            abs_path = "." + path
            if os.path.exists(abs_path):
                os.remove(abs_path)
    except:
        pass  # Không để crash ứng dụng


# =====================================================
# 📄 1️⃣ Trang hồ sơ học viên
# =====================================================
@router.get("/", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 303)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse("/auth/login", 303)

    # Đồng bộ avatar vào session để sidebar load đúng
    avatar = user.avatar_url or "/uploads/avatars/default-avatar.png"
    if request.session.get("user_avatar") != avatar:
        request.session["user_avatar"] = avatar

    major = db.query(Major).filter_by(id=user.major_id).first() if user.major_id else None
    academic_year = db.query(AcademicYear).filter_by(id=user.academic_year_id).first() if user.academic_year_id else None

    total_lessons = db.query(LessonProgress).filter_by(user_id=user_id).count()
    completed_lessons = (
        db.query(LessonProgress)
        .filter_by(user_id=user_id, progress_status="completed")
        .count()
    )
    total_quizzes = db.query(QuizAttempt).filter_by(user_id=user_id).count()
    total_assignments = (
        db.query(AssignmentSubmission).filter_by(student_id=user_id).count()
    )

    progress_percent = int((completed_lessons / total_lessons * 100) if total_lessons else 0)

    return templates["student"].TemplateResponse(
        "profile/profile.html",
        {
            "request": request,
            "user": user,
            "major": major,
            "academic_year": academic_year,
            "progress_percent": progress_percent,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "total_quizzes": total_quizzes,
            "total_assignments": total_assignments,
            "active_page": "profile",
        },
    )


# =====================================================
# 🖼️ 2️⃣ Upload avatar – Resize + Delete Old + Validation
# =====================================================

MAX_AVATAR_SIZE_MB = 5
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/upload-avatar")
async def upload_avatar(
    request: Request,
    files: Optional[list[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 303)

    if not files:
        return RedirectResponse("/student/profile?error=no_file", 303)

    os.makedirs(UPLOAD_AVATARS, exist_ok=True)

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/auth/login", 303)

    new_avatar_url = None

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()

        if ext not in ALLOWED_EXT or file.content_type not in ALLOWED_TYPES:
            continue

        contents = await file.read()
        size_mb = len(contents) / (1024 * 1024)

        if size_mb > MAX_AVATAR_SIZE_MB:
            return RedirectResponse("/student/profile?error=avatar_too_large", 303)

        # Resize ảnh về 512x512
        resized = resize_image(contents)

        filename = f"{uuid.uuid4()}.jpg"  # Lưu chuẩn JPG
        filepath = os.path.join(UPLOAD_AVATARS, filename)

        with open(filepath, "wb") as f:
            f.write(resized)

        new_avatar_url = f"/uploads/avatars/{filename}"

    if new_avatar_url:
        # Xoá avatar cũ
        delete_old_avatar(user.avatar_url)

        user.avatar_url = new_avatar_url
        user.updated_at = datetime.now()
        db.commit()

        # Đồng bộ session
        request.session["user_avatar"] = new_avatar_url

    return RedirectResponse("/student/profile?success=avatar_updated", 303)


# =====================================================
# 👤 3️⃣ Trang chỉnh sửa thông tin cá nhân (GET)
# =====================================================
@router.get("/edit", response_class=HTMLResponse)
def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 303)

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/auth/login", 303)

    majors = db.query(Major).all()
    years = db.query(AcademicYear).all()

    return templates["student"].TemplateResponse(
        "profile/edit_profile.html",
        {
            "request": request,
            "user": user,
            "majors": majors,
            "years": years,
            "active_page": "profile",
        },
    )


# =====================================================
# 💾 4️⃣ Xử lý cập nhật thông tin hồ sơ (POST)
# =====================================================
@router.post("/edit")
def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    phone: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    major_id: Optional[str] = Form(None),
    academic_year_id: Optional[str] = Form(None),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 303)

    try:
        user = db.query(User).filter_by(id=user_id).first()

        user.full_name = full_name
        user.phone = phone
        user.gender = gender
        user.date_of_birth = date_of_birth or None
        user.major_id = major_id or user.major_id
        user.academic_year_id = academic_year_id or user.academic_year_id
        user.updated_at = datetime.now()

        db.commit()
        return RedirectResponse("/student/profile?success=updated", 303)

    except Exception:
        traceback.print_exc()
        return RedirectResponse("/student/profile/edit?error=update_failed", 303)


# =====================================================
# 🔐 5️⃣ Trang đổi mật khẩu (GET)
# =====================================================
@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/auth/login", 303)

    return templates["student"].TemplateResponse(
        "profile/change_password.html",
        {"request": request, "active_page": "profile"},
    )


# =====================================================
# 💾 6️⃣ Xử lý đổi mật khẩu (POST)
# =====================================================
@router.post("/change-password")
def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 303)

    result = change_user_password(
        db=db,
        user_id=user_id,
        current_password=current_password,
        new_password=new_password,
        confirm_password=confirm_password,
    )

    if not result["success"]:
        return templates["student"].TemplateResponse(
            "profile/change_password.html",
            {
                "request": request,
                "error": result["message"],
                "active_page": "profile",
            },
            status_code=400,
        )

    # Log security: cập nhật ngày đổi mật khẩu
    security = db.query(SecuritySettings).filter_by(user_id=user_id).first()
    if security:
        security.last_password_change = datetime.now()
        db.commit()

    print(f"🔐 Student {user_id} đổi mật khẩu thành công.")
    request.session.clear()

    return RedirectResponse("/auth/login?msg=password_changed", 303)
