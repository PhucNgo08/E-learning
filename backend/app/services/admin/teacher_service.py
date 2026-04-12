import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.config.paths import UPLOAD_AVATARS
from app.models.user import User
from app.services import user_service
from app.services.common.auth_service import (
    DEFAULT_AVATAR_URL,
    TEACHER_ROLE_CODES,
    get_user_profile_context,
    hydrate_user_context,
    normalize_role_code,
    resolve_primary_role,
    upsert_user_profile,
)
from app.services.common.password_service import get_password_hash

VALID_ROLES = ["teacher", "teaching_assistant"]
UPLOAD_AVATARS.mkdir(parents=True, exist_ok=True)


# =====================================================
# HELPERS
# =====================================================
def _normalize_teacher_role(role: str | None) -> str:
    role_value = normalize_role_code(role)
    return role_value if role_value in TEACHER_ROLE_CODES else "teacher"


def _safe_filename_extension(filename: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    return ext if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"} else ".png"


# =====================================================
# 1. READ TEACHERS
# =====================================================
def get_all_teachers(db: Session):
    users = db.query(User).order_by(User.created_at.desc()).all()
    results = []
    for user in users:
        hydrate_user_context(db, user)
        if resolve_primary_role(db, user.id) in TEACHER_ROLE_CODES:
            results.append(user)
    return results


def get_teacher(db: Session, teacher_id: str):
    user = db.query(User).filter(User.id == teacher_id).first()
    if not user:
        return None

    hydrate_user_context(db, user)
    if resolve_primary_role(db, user.id) not in TEACHER_ROLE_CODES:
        return None
    return user


# =====================================================
# 2. CREATE TEACHER
# =====================================================
def create_teacher(db: Session, username: str, email: str, full_name: str, role: str):
    return user_service.create_user(
        username=username,
        email=email,
        password="123456",
        full_name=full_name,
        role=_normalize_teacher_role(role),
        db=db,
    )


# =====================================================
# 3. UPDATE TEACHER
# =====================================================
def update_teacher(db: Session, teacher_id: str, full_name: str, email: str, role: str):
    teacher = get_teacher(db, teacher_id)
    if not teacher:
        return None

    return user_service.update_user(
        user_id=teacher_id,
        username=teacher.username,
        email=email,
        password="",
        full_name=full_name,
        role=_normalize_teacher_role(role),
        db=db,
        major_id=getattr(teacher, "major_id", None),
    )


# =====================================================
# 4. UPDATE AVATAR
# =====================================================
def update_teacher_avatar(db: Session, teacher_id: str, file):
    teacher = get_teacher(db, teacher_id)
    if not teacher:
        return None

    ext = _safe_filename_extension(getattr(file, "filename", None))
    filename = f"{teacher_id}{ext}"
    avatar_path = UPLOAD_AVATARS / filename

    file_obj: BinaryIO = file.file
    with open(avatar_path, "wb") as output:
        shutil.copyfileobj(file_obj, output)

    current_profile = get_user_profile_context(db, teacher_id, teacher)
    upsert_user_profile(
        db,
        teacher_id,
        full_name=current_profile["full_name"] or teacher.username,
        phone=current_profile["phone"],
        avatar_url=f"/uploads/avatars/{filename}",
        date_of_birth=current_profile["date_of_birth"],
        gender=current_profile["gender"],
    )
    db.commit()

    refreshed = db.query(User).filter(User.id == teacher_id).first()
    return hydrate_user_context(db, refreshed)


# =====================================================
# 5. RESET PASSWORD
# =====================================================
def reset_teacher_password(db: Session, teacher_id: str):
    teacher = get_teacher(db, teacher_id)
    if not teacher:
        return None, None

    new_password = uuid.uuid4().hex[:8]
    teacher.password_hash = get_password_hash(new_password)
    db.commit()
    db.refresh(teacher)
    hydrate_user_context(db, teacher)
    return teacher, new_password
