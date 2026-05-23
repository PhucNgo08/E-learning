"""
==========================================================
👩‍🏫 ROUTER: Teacher - Profile
Quản lý hồ sơ giáo viên (xem, chỉnh sửa, đổi mật khẩu)
Tương thích schema refactor: users + user_profiles + teacher_profiles
==========================================================
"""

from datetime import datetime
from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.paths import PUBLIC_PATH, UPLOAD_AVATARS
from app.config.template_config import templates
from app.database.connection import get_db
from app.models.course import Course
from app.models.teacher_profiles import TeacherProfile
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.common.password_service import change_user_password


router = APIRouter(
    prefix="/teacher",
    tags=["Teacher - Profile"],
)

DEFAULT_AVATAR = f"{PUBLIC_PATH}/avatars/default-avatar.png"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def ensure_teacher_related_rows(user: User):
    if not user.profile:
        user.profile = UserProfile(
            user_id=user.id,
            full_name=user.username or user.email.split("@")[0],
        )

    if not user.teacher_profile:
        user.teacher_profile = TeacherProfile(user_id=user.id)


def save_avatar_file(file: UploadFile | None, old_url: str | None = None) -> str:
    if not file or not file.filename:
        return old_url or DEFAULT_AVATAR

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return old_url or DEFAULT_AVATAR

    if old_url and old_url != DEFAULT_AVATAR:
        try:
            old_name = Path(old_url).name
            old_path = Path(UPLOAD_AVATARS) / old_name
            if old_path.exists():
                old_path.unlink()
        except Exception:
            pass

    file_name = f"{uuid.uuid4().hex}{ext}"
    save_path = Path(UPLOAD_AVATARS) / file_name
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return f"{PUBLIC_PATH}/avatars/{file_name}"


@router.get("/profile", response_class=HTMLResponse)
async def teacher_profile(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    msg = request.query_params.get("msg")

    return templates["teacher"].TemplateResponse(
        "profile/profile.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "now": datetime.now(),
            "msg": msg,
        },
    )


@router.get("/profile/edit", response_class=HTMLResponse)
async def edit_profile_form(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    return templates["teacher"].TemplateResponse(
        "profile/profile_edit.html",
        {"request": request, "teacher": teacher},
    )


@router.post("/profile/edit")
async def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    avatar: UploadFile = File(None),
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    ensure_teacher_related_rows(teacher)

    avatar_url = save_avatar_file(avatar, teacher.avatar_url)

    teacher.profile.full_name = full_name.strip()
    teacher.email = email.strip()
    teacher.profile.phone = phone.strip() or None
    teacher.profile.avatar_url = avatar_url
    teacher.updated_at = datetime.utcnow()

    db.commit()
    return RedirectResponse(url="/teacher/profile?msg=updated", status_code=303)



@router.post("/profile/upload-avatar")
async def upload_teacher_avatar(
    request: Request,
    db: Session = Depends(get_db),
    avatar_file: UploadFile = File(None),
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy thông tin giáo viên.</h3>", status_code=404)

    ensure_teacher_related_rows(teacher)
    old_avatar = teacher.profile.avatar_url if teacher.profile else None
    avatar_url = save_avatar_file(avatar_file, old_avatar)
    teacher.profile.avatar_url = avatar_url
    teacher.updated_at = datetime.utcnow()

    request.session["user_avatar"] = avatar_url
    db.commit()

    return RedirectResponse(url="/teacher/dashboard", status_code=303)


@router.get("/profile/change-password", response_class=HTMLResponse)
async def change_password_form(request: Request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates["teacher"].TemplateResponse(
        "profile/change_password.html",
        {"request": request},
    )


@router.post("/profile/change-password")
async def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    result = change_user_password(
        db,
        user_id,
        current_password,
        new_password,
        confirm_password,
    )

    if not result["success"]:
        return templates["teacher"].TemplateResponse(
            "profile/change_password.html",
            {"request": request, "error": result["message"]},
            status_code=400,
        )

    request.session.clear()
    return RedirectResponse(url="/auth/login?msg=logout_after_change", status_code=303)