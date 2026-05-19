"""
==========================================================
🎓 ROUTER: Student - Profile
Bản đã sửa lỗi upload ảnh đại diện 422
Khớp template profile/edit/change-password
==========================================================
"""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional
import os
import traceback
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.config.paths import UPLOAD_AVATARS
from app.config.template_config import templates
from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.assignment_submission import AssignmentSubmission
from app.models.lesson_progress import LessonProgress
from app.models.major import Major
from app.models.quiz_attempt import QuizAttempt
from app.models.security_setting import SecuritySettings
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.common.password_service import change_user_password


router = APIRouter(
    prefix="/student/profile",
    tags=["Student - Profile"],
)

DEFAULT_AVATAR_URL = "/uploads/avatars/default-avatar.png"
MAX_AVATAR_SIZE_MB = 5
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")

    if not user_id or role != "student":
        return None

    return user_id


def resize_image(image_bytes: bytes, size=(512, 512)) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail(size, Image.LANCZOS)

    canvas = Image.new("RGB", size, (255, 255, 255))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))

    output = BytesIO()
    canvas.save(output, format="JPEG", quality=92)
    return output.getvalue()


def delete_old_avatar(old_url: str | None):
    try:
        if not old_url or "default-avatar.png" in old_url:
            return

        old_name = Path(old_url).name
        old_path = Path(UPLOAD_AVATARS) / old_name

        if old_path.exists():
            old_path.unlink()
    except Exception:
        pass


def ensure_student_related_rows(user: User):
    if not user.profile:
        user.profile = UserProfile(
            user_id=user.id,
            full_name=user.username or (user.email.split("@")[0] if user.email else "Student"),
        )

    if not user.student_profile:
        user.student_profile = StudentProfile(user_id=user.id)


def get_student_major(user: User):
    if getattr(user, "student_profile", None) and getattr(user.student_profile, "major", None):
        return user.student_profile.major

    return getattr(user, "major", None)


def get_student_academic_year(user: User):
    if getattr(user, "student_profile", None) and getattr(user.student_profile, "academic_year", None):
        return user.student_profile.academic_year

    return getattr(user, "academic_year", None)


@router.get("/", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    ensure_student_related_rows(user)
    db.commit()
    db.refresh(user)

    avatar = (
        getattr(user.profile, "avatar_url", None)
        or getattr(user, "avatar_url", None)
        or DEFAULT_AVATAR_URL
    )

    if request.session.get("user_avatar") != avatar:
        request.session["user_avatar"] = avatar

    major = get_student_major(user)
    academic_year = get_student_academic_year(user)

    total_lessons = db.query(LessonProgress).filter_by(user_id=user_id).count()

    completed_lessons = (
        db.query(LessonProgress)
        .filter_by(user_id=user_id, progress_status="completed")
        .count()
    )

    total_quizzes = db.query(QuizAttempt).filter_by(user_id=user_id).count()

    total_assignments = (
        db.query(AssignmentSubmission)
        .filter_by(student_id=user_id)
        .count()
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


@router.post("/upload-avatar")
async def upload_avatar(
    request: Request,
    avatar: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

    if not avatar or not avatar.filename:
        return RedirectResponse("/student/profile?error=no_file", status_code=303)

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    ensure_student_related_rows(user)
    os.makedirs(UPLOAD_AVATARS, exist_ok=True)

    try:
        ext = os.path.splitext(avatar.filename)[1].lower()

        if ext not in ALLOWED_EXT:
            return RedirectResponse("/student/profile?error=avatar_invalid_type", status_code=303)

        if avatar.content_type not in ALLOWED_TYPES:
            return RedirectResponse("/student/profile?error=avatar_invalid_type", status_code=303)

        contents = await avatar.read()
        if not contents:
            return RedirectResponse("/student/profile?error=no_file", status_code=303)

        size_mb = len(contents) / (1024 * 1024)
        if size_mb > MAX_AVATAR_SIZE_MB:
            return RedirectResponse("/student/profile?error=avatar_too_large", status_code=303)

        resized = resize_image(contents)

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(UPLOAD_AVATARS, filename)

        with open(filepath, "wb") as f:
            f.write(resized)

        new_avatar_url = f"/uploads/avatars/{filename}"

        old_avatar = (
            getattr(user.profile, "avatar_url", None)
            or getattr(user, "avatar_url", None)
        )
        delete_old_avatar(old_avatar)

        user.profile.avatar_url = new_avatar_url
        user.updated_at = datetime.utcnow()

        db.commit()
        request.session["user_avatar"] = new_avatar_url

        return RedirectResponse("/student/profile?success=avatar_updated", status_code=303)

    except UnidentifiedImageError:
        db.rollback()
        return RedirectResponse("/student/profile?error=avatar_invalid_type", status_code=303)

    except Exception:
        traceback.print_exc()
        db.rollback()
        return RedirectResponse("/student/profile?error=avatar_upload_failed", status_code=303)

@router.get("/edit", response_class=HTMLResponse)
def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

    user = db.query(User).filter_by(id=user_id).first()

    if not user:
        return RedirectResponse("/auth/login", status_code=303)

    ensure_student_related_rows(user)
    db.commit()
    db.refresh(user)

    majors = db.query(Major).order_by(Major.major_name.asc()).all()
    years = db.query(AcademicYear).order_by(AcademicYear.start_year.desc()).all()

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
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

    try:
        user = db.query(User).filter_by(id=user_id).first()

        if not user:
            return RedirectResponse("/auth/login", status_code=303)

        ensure_student_related_rows(user)

        user.profile.full_name = full_name.strip()
        user.profile.phone = phone.strip() if phone else None
        user.profile.gender = gender or None

        user.profile.date_of_birth = (
            datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            if date_of_birth else None
        )

        user.student_profile.major_id = major_id or None
        user.student_profile.academic_year_id = academic_year_id or None
        user.updated_at = datetime.utcnow()

        db.commit()

        return RedirectResponse("/student/profile?success=updated", status_code=303)

    except Exception:
        traceback.print_exc()
        db.rollback()
        return RedirectResponse("/student/profile/edit?error=update_failed", status_code=303)


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

    return templates["student"].TemplateResponse(
        "profile/change_password.html",
        {
            "request": request,
            "active_page": "profile",
        },
    )


@router.post("/change-password")
def change_password(
    request: Request,
    db: Session = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    user_id = get_current_student_id(request)

    if not user_id:
        return RedirectResponse("/auth/login", status_code=303)

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

    security = db.query(SecuritySettings).filter_by(user_id=user_id).first()

    if security:
        security.last_password_change = datetime.utcnow()
        db.commit()

    request.session.clear()

    return RedirectResponse("/auth/login?msg=password_changed", status_code=303)
