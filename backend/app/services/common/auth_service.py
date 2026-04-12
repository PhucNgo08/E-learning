from __future__ import annotations

import hashlib
import re
import time
import unicodedata
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, status
from passlib.hash import pbkdf2_sha256
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.security_setting import SecuritySettings
from app.models.user import User

settings = get_settings()

REMEMBER_ME_DAYS = 7
DEFAULT_AVATAR_URL = "/uploads/avatars/default-avatar.png"

ROLE_PRIORITY = ["admin", "teacher", "teaching_assistant", "student"]
VALID_ROLE_CODES = set(ROLE_PRIORITY)
TEACHER_ROLE_CODES = {"teacher", "teaching_assistant"}


# =====================================================
# PASSWORD HASH / VERIFY
# =====================================================
def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False

    try:
        if hashed.startswith("$pbkdf2-sha256$"):
            return pbkdf2_sha256.verify(plain, hashed)
    except Exception:
        return False

    if hashed.startswith("$2a$") or hashed.startswith("$2b$") or hashed.startswith("$2y$"):
        try:
            from app.services.common.password_service import verify_password as bcrypt_verify

            return bcrypt_verify(plain, hashed)
        except Exception:
            return False

    return hashlib.sha256(plain.encode()).hexdigest() == hashed


def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


# =====================================================
# COMMON NORMALIZERS
# =====================================================
def normalize_username(email: str) -> str:
    base = (email or "").split("@")[0].strip()
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-zA-Z0-9_]", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return (base or f"user_{uuid.uuid4().hex[:8]}").lower()


def normalize_role_code(role_code: str | None, default: str = "student") -> str:
    role = str(role_code or "").strip().lower()
    return role if role in VALID_ROLE_CODES else default


def build_dashboard_redirect(role_code: str | None) -> str:
    role = str(role_code or "").strip().lower()
    if role == "admin":
        return "/admin/dashboard"
    if role in TEACHER_ROLE_CODES:
        return "/teacher/dashboard"
    return "/student/dashboard"


# =====================================================
# LOOKUPS
# =====================================================
def get_user_by_identifier(db: Session, identifier: str) -> User | None:
    login_id = (identifier or "").strip().lower()
    if not login_id:
        return None

    query = db.query(User)
    if "@" in login_id:
        return query.filter(User.email == login_id).first()
    return query.filter(User.username == login_id).first()


def ensure_security_settings(db: Session, user_id: str) -> SecuritySettings:
    security = db.query(SecuritySettings).filter(SecuritySettings.user_id == user_id).first()
    if security:
        return security

    security = SecuritySettings(id=str(uuid.uuid4()), user_id=user_id)
    db.add(security)
    db.flush()
    return security


def _get_role_rows(db: Session, user_id: str) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT r.role_code
            FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).scalars().all()

    return [str(r).strip().lower() for r in rows if r]


def _get_permission_rows(db: Session, user_id: str) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT p.permission_code
            FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).scalars().all()

    return [str(r).strip().lower() for r in rows if r]


def resolve_user_roles(db: Session, user_id: str, user: User | None = None) -> list[str]:
    raw_roles = _get_role_rows(db, user_id)

    normalized: list[str] = []
    for role in raw_roles:
        role_code = str(role).strip().lower()
        if role_code in VALID_ROLE_CODES:
            normalized.append(role_code)

    return sorted(
        set(normalized),
        key=lambda item: ROLE_PRIORITY.index(item) if item in ROLE_PRIORITY else 999,
    )


def resolve_primary_role(db: Session, user_id: str, user: User | None = None) -> str:
    roles = resolve_user_roles(db, user_id, user)
    return roles[0] if roles else ""


def resolve_user_permissions(db: Session, user_id: str) -> list[str]:
    return sorted(set(_get_permission_rows(db, user_id)))


def get_user_profile_context(db: Session, user_id: str, user: User | None = None) -> dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT
                up.full_name,
                up.phone,
                up.avatar_url,
                up.date_of_birth,
                up.gender,
                sp.mssv,
                sp.academic_year_id,
                sp.major_id AS student_major_id,
                tp.major_id AS teacher_major_id,
                tp.employee_code
            FROM users u
            LEFT JOIN user_profiles up ON up.user_id = u.id
            LEFT JOIN student_profiles sp ON sp.user_id = u.id
            LEFT JOIN teacher_profiles tp ON tp.user_id = u.id
            WHERE u.id = :user_id
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    fallback_name = None
    if user is not None:
        fallback_name = getattr(user, "username", None) or getattr(user, "email", None)

    full_name = None
    avatar_url = DEFAULT_AVATAR_URL
    phone = None
    date_of_birth = None
    gender = None
    mssv = None
    academic_year_id = None
    major_id = None
    employee_code = None

    if row:
        full_name = row.get("full_name") or fallback_name
        avatar_url = row.get("avatar_url") or DEFAULT_AVATAR_URL
        phone = row.get("phone")
        date_of_birth = row.get("date_of_birth")
        gender = row.get("gender")
        mssv = row.get("mssv")
        academic_year_id = row.get("academic_year_id")
        major_id = row.get("teacher_major_id") or row.get("student_major_id")
        employee_code = row.get("employee_code")
    else:
        full_name = fallback_name

    return {
        "full_name": full_name,
        "avatar_url": avatar_url,
        "phone": phone,
        "date_of_birth": date_of_birth,
        "gender": gender,
        "mssv": mssv,
        "academic_year_id": academic_year_id,
        "major_id": major_id,
        "employee_code": employee_code,
    }


def _safe_setattr(obj: Any, name: str, value: Any) -> None:
    try:
        setattr(obj, name, value)
    except Exception:
        pass


def hydrate_user_context(db: Session, user: User | None) -> User | None:
    if user is None:
        return None

    ctx = get_user_profile_context(db, user.id, user)
    all_roles = resolve_user_roles(db, user.id, user)
    primary_role = all_roles[0] if all_roles else ""
    permissions = resolve_user_permissions(db, user.id)

    _safe_setattr(user, "full_name", ctx["full_name"])
    _safe_setattr(user, "avatar_url", ctx["avatar_url"])
    _safe_setattr(user, "phone", ctx["phone"])
    _safe_setattr(user, "date_of_birth", ctx["date_of_birth"])
    _safe_setattr(user, "gender", ctx["gender"])
    _safe_setattr(user, "mssv", ctx["mssv"])
    _safe_setattr(user, "academic_year_id", ctx["academic_year_id"])
    _safe_setattr(user, "major_id", ctx["major_id"])
    _safe_setattr(user, "employee_code", ctx["employee_code"])

    _safe_setattr(user, "resolved_full_name", ctx["full_name"])
    _safe_setattr(user, "resolved_avatar_url", ctx["avatar_url"])
    _safe_setattr(user, "resolved_role", primary_role)
    _safe_setattr(user, "resolved_roles", all_roles)
    _safe_setattr(user, "resolved_permissions", permissions)

    return user


# =====================================================
# PROFILE / ROLE UPSERTS WITHOUT ORM MODELS
# =====================================================
def _row_exists(db: Session, table_name: str, user_id: str) -> bool:
    return bool(
        db.execute(
            text(f"SELECT 1 FROM {table_name} WHERE user_id = :user_id LIMIT 1"),
            {"user_id": user_id},
        ).scalar()
    )


def upsert_user_profile(
    db: Session,
    user_id: str,
    *,
    full_name: str,
    phone: str | None = None,
    avatar_url: str | None = None,
    date_of_birth: Any = None,
    gender: str | None = None,
) -> None:
    payload = {
        "user_id": user_id,
        "full_name": (full_name or "").strip(),
        "phone": (phone or None),
        "avatar_url": avatar_url or DEFAULT_AVATAR_URL,
        "date_of_birth": date_of_birth,
        "gender": gender or None,
    }

    if not payload["full_name"]:
        raise ValueError("Họ tên không được để trống.")

    if _row_exists(db, "user_profiles", user_id):
        db.execute(
            text(
                """
                UPDATE user_profiles
                SET full_name = :full_name,
                    phone = :phone,
                    avatar_url = :avatar_url,
                    date_of_birth = :date_of_birth,
                    gender = :gender,
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            payload,
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO user_profiles (
                    user_id, full_name, phone, avatar_url, date_of_birth, gender, created_at, updated_at
                ) VALUES (
                    :user_id, :full_name, :phone, :avatar_url, :date_of_birth, :gender, NOW(), NOW()
                )
                """
            ),
            payload,
        )


def upsert_student_profile(
    db: Session,
    user_id: str,
    *,
    mssv: str | None = None,
    academic_year_id: str | None = None,
    major_id: str | None = None,
    enrollment_status: str = "active",
) -> None:
    payload = {
        "user_id": user_id,
        "mssv": (mssv or None),
        "academic_year_id": academic_year_id or None,
        "major_id": major_id or None,
        "enrollment_status": enrollment_status or "active",
    }

    if _row_exists(db, "student_profiles", user_id):
        db.execute(
            text(
                """
                UPDATE student_profiles
                SET mssv = :mssv,
                    academic_year_id = :academic_year_id,
                    major_id = :major_id,
                    enrollment_status = :enrollment_status,
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            payload,
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO student_profiles (
                    user_id, mssv, academic_year_id, major_id, enrollment_status, created_at, updated_at
                ) VALUES (
                    :user_id, :mssv, :academic_year_id, :major_id, :enrollment_status, NOW(), NOW()
                )
                """
            ),
            payload,
        )


def upsert_teacher_profile(
    db: Session,
    user_id: str,
    *,
    major_id: str | None = None,
    employee_code: str | None = None,
    bio: str | None = None,
) -> None:
    payload = {
        "user_id": user_id,
        "employee_code": employee_code or None,
        "major_id": major_id or None,
        "bio": bio or None,
    }

    if _row_exists(db, "teacher_profiles", user_id):
        db.execute(
            text(
                """
                UPDATE teacher_profiles
                SET employee_code = COALESCE(:employee_code, employee_code),
                    major_id = :major_id,
                    bio = COALESCE(:bio, bio),
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            payload,
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO teacher_profiles (
                    user_id, employee_code, major_id, bio, total_assignments_created, created_at, updated_at
                ) VALUES (
                    :user_id, :employee_code, :major_id, :bio, 0, NOW(), NOW()
                )
                """
            ),
            payload,
        )


def clear_student_profile(db: Session, user_id: str) -> None:
    db.execute(text("DELETE FROM student_profiles WHERE user_id = :user_id"), {"user_id": user_id})


def clear_teacher_profile(db: Session, user_id: str) -> None:
    db.execute(text("DELETE FROM teacher_profiles WHERE user_id = :user_id"), {"user_id": user_id})


def assign_primary_role(db: Session, user_id: str, role_code: str) -> None:
    normalized_role = normalize_role_code(role_code)
    role_id = db.execute(
        text("SELECT id FROM roles WHERE role_code = :role_code LIMIT 1"),
        {"role_code": normalized_role},
    ).scalar()

    if not role_id:
        raise ValueError(f"Role '{normalized_role}' không tồn tại trong bảng roles.")

    db.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id})
    db.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            VALUES (:user_id, :role_id, NOW())
            """
        ),
        {"user_id": user_id, "role_id": role_id},
    )


# =====================================================
# AUTHENTICATE / SESSION
# =====================================================
def authenticate_user(db: Session, identifier: str, password: str) -> dict[str, Any]:
    user = get_user_by_identifier(db, identifier)
    if not user:
        return {"success": False, "message": "❌ Không tìm thấy tài khoản."}

    security = ensure_security_settings(db, user.id)

    if security.account_locked_until and security.account_locked_until > datetime.utcnow():
        return {
            "success": False,
            "message": f"🔒 Tài khoản đang bị khóa đến {security.account_locked_until:%H:%M:%S %d/%m/%Y}.",
        }

    status_val = str(getattr(user, "status", "active") or "active").strip().lower()
    if status_val not in {"active", "1", "true", "enabled"}:
        return {"success": False, "message": "🚫 Tài khoản đã bị vô hiệu hóa."}

    if not verify_password(password, user.password_hash):
        security.failed_login_attempts = (security.failed_login_attempts or 0) + 1
        if security.failed_login_attempts >= 5:
            security.failed_login_attempts = 0
            security.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.commit()
            return {"success": False, "message": "🔒 Sai 5 lần — tài khoản bị khóa 30 phút."}

        db.commit()
        remaining = 5 - (security.failed_login_attempts or 0)
        return {"success": False, "message": f"⚠️ Mật khẩu sai. Còn {remaining} lần thử."}

    security.failed_login_attempts = 0
    security.account_locked_until = None
    user.last_login = datetime.utcnow()
    user.login_count = int(getattr(user, "login_count", 0) or 0) + 1
    db.commit()
    db.refresh(user)
    hydrate_user_context(db, user)

    resolved_roles = getattr(user, "resolved_roles", None) or []
    if not resolved_roles:
        return {"success": False, "message": "🚫 Tài khoản chưa được gán vai trò trong hệ thống."}

    return {"success": True, "user": user}


def create_user_session(request: Request, db: Session, user: User, remember_me: bool = False) -> None:
    hydrate_user_context(db, user)

    request.session.clear()

    roles = getattr(user, "resolved_roles", None) or resolve_user_roles(db, user.id, user)
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản chưa được gán vai trò trong hệ thống.",
        )

    permissions = getattr(user, "resolved_permissions", None) or resolve_user_permissions(db, user.id)

    role = roles[0]
    full_name = getattr(user, "resolved_full_name", None) or getattr(user, "full_name", None) or user.username
    avatar_url = getattr(user, "resolved_avatar_url", None) or getattr(user, "avatar_url", None) or DEFAULT_AVATAR_URL

    client_ip = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "Unknown-UA")
    now_ts = time.time()

    expiry_seconds = REMEMBER_ME_DAYS * 24 * 60 * 60 if remember_me else settings.session_max_age_seconds
    expires_at_ts = now_ts + expiry_seconds

    request.session.update(
        {
            "session_version": uuid.uuid4().hex,
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": full_name,
            "user_full_name": full_name,
            "role": role,
            "user_role": role,
            "roles": roles,
            "user_roles": roles,
            "permissions": permissions,
            "user_permissions": permissions,
            "avatar": avatar_url,
            "user_avatar": avatar_url,
            "session_ip": client_ip,
            "session_ua": user_agent,
            "last_active": now_ts,
            "expires_at_ts": expires_at_ts,
            "remember_me": bool(remember_me),
        }
    )


# =====================================================
# SOCIAL LOGIN
# =====================================================
def detect_role_from_email(email: str) -> str:
    email = (email or "").strip().lower()
    if email.endswith("@gv.hutech.edu.vn"):
        return "teacher"
    if email.endswith("@st.hutech.edu.vn"):
        return "student"
    return "student"


def generate_unique_username(db: Session, email: str) -> str:
    base = normalize_username(email)
    candidate = base
    counter = 1

    while db.query(User).filter(User.username == candidate).first():
        counter += 1
        candidate = f"{base}_{counter}"

    return candidate


def get_or_create_social_user(
    db: Session,
    email: str,
    full_name: str,
    avatar: str | None = None,
    role_code: str | None = None,
) -> User:
    email = (email or "").strip().lower()
    if not email:
        raise ValueError("Email social login không hợp lệ.")

    user = db.query(User).filter(User.email == email).first()
    if user:
        hydrate_user_context(db, user)
        return user

    username = generate_unique_username(db, email)
    role = normalize_role_code(role_code or detect_role_from_email(email))

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=hash_password(uuid.uuid4().hex),
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    upsert_user_profile(
        db,
        user.id,
        full_name=(full_name or username).strip() or username,
        avatar_url=avatar or DEFAULT_AVATAR_URL,
    )
    assign_primary_role(db, user.id, role)

    if role == "student":
        upsert_student_profile(db, user.id, enrollment_status="active")
        clear_teacher_profile(db, user.id)
    elif role in TEACHER_ROLE_CODES:
        upsert_teacher_profile(db, user.id)
        clear_student_profile(db, user.id)
    else:
        clear_student_profile(db, user.id)
        clear_teacher_profile(db, user.id)

    ensure_security_settings(db, user.id)
    db.commit()
    db.refresh(user)
    hydrate_user_context(db, user)
    return user


# =====================================================
# ADMIN CREATE USER
# =====================================================
def create_user(db: Session, email: str, full_name: str, password: str, role: str = "student") -> User:
    email = (email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email không được để trống")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    username = generate_unique_username(db, email)
    normalized_role = normalize_role_code(role)

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password_hash=hash_password(password or "123456"),
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    upsert_user_profile(db, user.id, full_name=full_name or username, avatar_url=DEFAULT_AVATAR_URL)
    assign_primary_role(db, user.id, normalized_role)

    if normalized_role == "student":
        upsert_student_profile(db, user.id, enrollment_status="active")
        clear_teacher_profile(db, user.id)
    elif normalized_role in TEACHER_ROLE_CODES:
        upsert_teacher_profile(db, user.id)
        clear_student_profile(db, user.id)
    else:
        clear_student_profile(db, user.id)
        clear_teacher_profile(db, user.id)

    ensure_security_settings(db, user.id)
    db.commit()
    db.refresh(user)
    hydrate_user_context(db, user)
    return user


# =====================================================
# LOGOUT
# =====================================================
def logout_user(request: Request) -> None:
    request.session.clear()