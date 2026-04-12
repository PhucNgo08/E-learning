import re
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.security_setting import SecuritySettings
from app.models.user import User
from app.services.common.auth_service import (
    TEACHER_ROLE_CODES,
    assign_primary_role,
    clear_student_profile,
    clear_teacher_profile,
    ensure_security_settings,
    hydrate_user_context,
    normalize_role_code,
    resolve_primary_role,
    upsert_student_profile,
    upsert_teacher_profile,
    upsert_user_profile,
)
from app.services.common.password_service import get_password_hash


# =====================================================
# INTERNAL HELPERS
# =====================================================
_PASSWORD_POLICY_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*@).{8,}$")


def _clean_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _normalize_email(email: str | None) -> str:
    value = (email or "").strip().lower()
    if not value:
        raise ValueError("Email không được để trống.")
    return value


def _normalize_username(username: str | None) -> str:
    value = (username or "").strip()
    if not value:
        raise ValueError("Tên đăng nhập không được để trống.")
    return value


def _validate_password_policy(password: str | None) -> str:
    value = (password or "").strip()

    if not value:
        raise ValueError("Mật khẩu không được để trống.")

    if len(value) < 8:
        raise ValueError("Mật khẩu phải có ít nhất 8 ký tự.")

    if "@" not in value:
        raise ValueError("Mật khẩu bắt buộc phải chứa ký tự @.")

    if not any(ch.isupper() for ch in value):
        raise ValueError("Mật khẩu bắt buộc phải có ít nhất 1 chữ in hoa.")

    if not _PASSWORD_POLICY_REGEX.match(value):
        raise ValueError("Mật khẩu chưa đúng định dạng yêu cầu.")

    return value


def _ensure_unique_username_email(db: Session, username: str, email: str, current_user_id: str | None = None) -> None:
    username_query = db.query(User).filter(User.username == username)
    email_query = db.query(User).filter(User.email == email)

    if current_user_id:
        username_query = username_query.filter(User.id != current_user_id)
        email_query = email_query.filter(User.id != current_user_id)

    if username_query.first():
        raise ValueError("Tên đăng nhập đã tồn tại.")
    if email_query.first():
        raise ValueError("Email đã tồn tại.")


def _ensure_unique_mssv(db: Session, mssv: str | None, current_user_id: str | None = None) -> None:
    mssv = _clean_text(mssv)
    if not mssv:
        return

    sql = "SELECT user_id FROM student_profiles WHERE mssv = :mssv LIMIT 1"
    found_user_id = db.execute(text(sql), {"mssv": mssv}).scalar()
    if found_user_id and found_user_id != current_user_id:
        raise ValueError("MSSV đã tồn tại.")


def _sync_role_specific_profile(
    db: Session,
    *,
    user_id: str,
    username: str,
    role: str,
    academic_year_id: str | None,
    major_id: str | None,
    mssv: str | None,
) -> None:
    if role == "student":
        upsert_student_profile(
            db,
            user_id,
            mssv=_clean_text(mssv) or username,
            academic_year_id=academic_year_id,
            major_id=major_id,
            enrollment_status="active",
        )
        clear_teacher_profile(db, user_id)
        return

    if role in TEACHER_ROLE_CODES:
        upsert_teacher_profile(db, user_id, major_id=major_id)
        clear_student_profile(db, user_id)
        return

    clear_student_profile(db, user_id)
    clear_teacher_profile(db, user_id)


def _is_admin_user(db: Session, user_id: str) -> bool:
    return resolve_primary_role(db, user_id) == "admin"


# =====================================================
# 1. CREATE USER
# =====================================================
def create_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str,
    db: Session,
    academic_year_id: str = None,
    major_id: str = None,
    mssv: str = None,
):
    try:
        username = _normalize_username(username)
        email = _normalize_email(email)
        full_name = _clean_text(full_name)
        role = normalize_role_code(role)
        password = _validate_password_policy(password)

        if not full_name:
            raise ValueError("Họ tên không được để trống.")

        _ensure_unique_username_email(db, username, email)
        if role == "student":
            _ensure_unique_mssv(db, mssv or username)

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

        upsert_user_profile(db, user.id, full_name=full_name)
        assign_primary_role(db, user.id, role)
        _sync_role_specific_profile(
            db,
            user_id=user.id,
            username=username,
            role=role,
            academic_year_id=academic_year_id,
            major_id=major_id,
            mssv=mssv,
        )
        ensure_security_settings(db, user.id)

        db.commit()
        db.refresh(user)
        return hydrate_user_context(db, user)

    except (ValueError, SQLAlchemyError) as exc:
        db.rollback()
        if isinstance(exc, ValueError):
            raise
        raise RuntimeError(f"Lỗi khi tạo người dùng: {exc}") from exc


# =====================================================
# 2. READ USERS
# =====================================================
def get_user_by_id(user_id: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    return hydrate_user_context(db, user)


def get_user_by_email(email: str, db: Session):
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    user = db.query(User).filter(User.email == normalized).first()
    return hydrate_user_context(db, user)


def get_all_users(db: Session):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [hydrate_user_context(db, user) for user in users]


# =====================================================
# 3. UPDATE USER
# =====================================================
def update_user(
    user_id: str,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str,
    db: Session,
    academic_year_id: str = None,
    major_id: str = None,
    mssv: str = None,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    try:
        username = _normalize_username(username)
        email = _normalize_email(email)
        full_name = _clean_text(full_name)
        role = normalize_role_code(role)

        if not full_name:
            raise ValueError("Họ tên không được để trống.")

        _ensure_unique_username_email(db, username, email, current_user_id=user_id)
        if role == "student":
            _ensure_unique_mssv(db, mssv or username, current_user_id=user_id)

        user.username = username
        user.email = email
        user.updated_at = datetime.utcnow()

        if password and password.strip():
            new_password = _validate_password_policy(password)
            user.password_hash = get_password_hash(new_password)

        upsert_user_profile(db, user.id, full_name=full_name)
        assign_primary_role(db, user.id, role)
        _sync_role_specific_profile(
            db,
            user_id=user.id,
            username=username,
            role=role,
            academic_year_id=academic_year_id,
            major_id=major_id,
            mssv=mssv,
        )
        ensure_security_settings(db, user.id)

        db.commit()
        db.refresh(user)
        return hydrate_user_context(db, user)

    except (ValueError, SQLAlchemyError) as exc:
        db.rollback()
        if isinstance(exc, ValueError):
            raise
        raise RuntimeError(f"Lỗi khi cập nhật người dùng: {exc}") from exc


# =====================================================
# 4. UPDATE PASSWORD
# =====================================================
def update_password(db: Session, email: str, new_password: str):
    user = db.query(User).filter(User.email == _normalize_email(email)).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng với email này.")

    new_password = _validate_password_policy(new_password)

    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(user)
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise RuntimeError(f"Lỗi khi đặt lại mật khẩu: {exc}") from exc


# =====================================================
# 5. DEACTIVATE USER
# =====================================================
def deactivate_user(user_id: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    if str(user.status).lower() == "inactive":
        raise ValueError("Tài khoản đã bị vô hiệu hóa.")

    if _is_admin_user(db, user_id):
        raise ValueError("Không thể vô hiệu hóa tài khoản quản trị viên chính.")

    user.status = "inactive"
    user.updated_at = datetime.utcnow()

    sec = db.query(SecuritySettings).filter(SecuritySettings.user_id == user_id).first()
    if sec:
        sec.failed_login_attempts = 0
        sec.account_locked_until = None

    try:
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise RuntimeError(f"Lỗi khi vô hiệu hóa tài khoản: {exc}") from exc


# =====================================================
# 6. RESTORE USER
# =====================================================
def restore_user(user_id: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    if str(user.status).lower() == "active":
        raise ValueError("Tài khoản đang hoạt động.")

    user.status = "active"
    user.updated_at = datetime.utcnow()

    sec = db.query(SecuritySettings).filter(SecuritySettings.user_id == user_id).first()
    if sec:
        sec.failed_login_attempts = 0
        sec.account_locked_until = None

    try:
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        raise RuntimeError(f"Lỗi khi khôi phục tài khoản: {exc}") from exc


# =====================================================
# 7. DELETE DEPENDENCIES CHECK
# =====================================================
def get_user_delete_dependencies(user_id: str, db: Session) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    checks = {
        "lớp chủ nhiệm": "SELECT COUNT(*) FROM classes WHERE homeroom_teacher_id = :user_id",
        "khóa học đang phụ trách": "SELECT COUNT(*) FROM courses WHERE teacher_id = :user_id",
        "lớp học phần đang dạy": "SELECT COUNT(*) FROM course_sections WHERE teacher_id = :user_id",
        "đơn hàng": "SELECT COUNT(*) FROM orders WHERE user_id = :user_id",
        "khóa học đã mua": "SELECT COUNT(*) FROM user_courses WHERE user_id = :user_id",
        "học liệu đã tạo": "SELECT COUNT(*) FROM course_materials WHERE created_by = :user_id",
        "ngân hàng câu hỏi": "SELECT COUNT(*) FROM question_bank WHERE created_by = :user_id",
        "mẫu quiz": "SELECT COUNT(*) FROM quiz_templates WHERE created_by = :user_id",
        "bài tập đã giao": "SELECT COUNT(*) FROM assignments WHERE teacher_id = :user_id",
        "bài nộp của sinh viên": "SELECT COUNT(*) FROM assignment_submissions WHERE student_id = :user_id",
        "nhóm bài tập đang làm trưởng nhóm": "SELECT COUNT(*) FROM assignment_groups WHERE leader_id = :user_id",
    }

    dependencies = {}
    for label, sql in checks.items():
        try:
            count = db.execute(text(sql), {"user_id": user_id}).scalar() or 0
            if count > 0:
                dependencies[label] = count
        except Exception:
            continue

    return dependencies


def _format_dependency_summary(dependencies: dict) -> str:
    if not dependencies:
        return ""
    return ", ".join([f"{name}: {count}" for name, count in dependencies.items()])


# =====================================================
# 8. SMART DELETE
# =====================================================
def delete_user_safely(user_id: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    if _is_admin_user(db, user_id):
        raise ValueError("Không thể xóa tài khoản quản trị viên.")

    dependencies = get_user_delete_dependencies(user_id, db)
    if dependencies:
        if str(user.status).lower() != "inactive":
            deactivate_user(user_id, db)

        return {
            "action": "deactivated",
            "message": (
                "Tài khoản còn dữ liệu liên kết nên hệ thống đã chuyển sang vô hiệu hóa "
                f"thay vì xóa vĩnh viễn. ({_format_dependency_summary(dependencies)})"
            ),
            "dependencies": dependencies,
        }

    try:
        nullable_updates = [
            "UPDATE class_enrollments SET approved_by = NULL WHERE approved_by = :user_id",
            "UPDATE course_enrollments SET approved_by = NULL WHERE approved_by = :user_id",
            "UPDATE quiz_attempts SET graded_by = NULL WHERE graded_by = :user_id",
            "UPDATE course_reviews SET moderated_by = NULL WHERE moderated_by = :user_id",
            "UPDATE assignment_submissions SET graded_by = NULL WHERE graded_by = :user_id",
            "UPDATE api_request_logs SET user_id = NULL WHERE user_id = :user_id",
        ]

        for sql in nullable_updates:
            try:
                db.execute(text(sql), {"user_id": user_id})
            except Exception:
                continue

        sec = db.query(SecuritySettings).filter(SecuritySettings.user_id == user_id).first()
        if sec:
            db.delete(sec)

        db.delete(user)
        db.commit()
        return {"action": "deleted", "message": "Đã xóa vĩnh viễn tài khoản.", "dependencies": {}}

    except SQLAlchemyError as exc:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa tài khoản: {exc}") from exc


# =====================================================
# 9. HARD DELETE
# =====================================================
def delete_user_permanently(user_id: str, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    if _is_admin_user(db, user_id):
        raise ValueError("Không thể xóa tài khoản quản trị viên.")

    dependencies = get_user_delete_dependencies(user_id, db)
    if dependencies:
        raise ValueError(
            "Không thể xóa vĩnh viễn vì tài khoản vẫn còn dữ liệu liên kết: "
            + _format_dependency_summary(dependencies)
        )

    try:
        nullable_updates = [
            "UPDATE class_enrollments SET approved_by = NULL WHERE approved_by = :user_id",
            "UPDATE course_enrollments SET approved_by = NULL WHERE approved_by = :user_id",
            "UPDATE quiz_attempts SET graded_by = NULL WHERE graded_by = :user_id",
            "UPDATE course_reviews SET moderated_by = NULL WHERE moderated_by = :user_id",
            "UPDATE assignment_submissions SET graded_by = NULL WHERE graded_by = :user_id",
            "UPDATE api_request_logs SET user_id = NULL WHERE user_id = :user_id",
        ]

        for sql in nullable_updates:
            try:
                db.execute(text(sql), {"user_id": user_id})
            except Exception:
                continue

        sec = db.query(SecuritySettings).filter(SecuritySettings.user_id == user_id).first()
        if sec:
            db.delete(sec)

        db.delete(user)
        db.commit()
        return True

    except SQLAlchemyError as exc:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa vĩnh viễn tài khoản: {exc}") from exc