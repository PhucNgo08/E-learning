from __future__ import annotations

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.class_enrollment import ClassEnrollment
from app.models.user import User

ACTIVE_CLASS_ENROLLMENT_STATUSES = {"active", "approved"}
INACTIVE_CLASS_ENROLLMENT_STATUSES = {"rejected", "removed", "cancelled", "completed"}
ALLOWED_CLASS_ENROLLMENT_STATUSES = {
    "applied",
    "approved",
    "active",
    "rejected",
    "removed",
    "cancelled",
    "completed",
}


def _now() -> datetime:
    return datetime.utcnow()


def _normalize_status(status: str | None, default: str = "active") -> str:
    return (status or default).strip().lower()


def get_class_by_id(db: Session, class_id: str) -> Optional[Class]:
    return db.query(Class).filter(Class.id == class_id).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_enrollment_by_id(db: Session, enrollment_id: str) -> Optional[ClassEnrollment]:
    return db.query(ClassEnrollment).filter(ClassEnrollment.id == enrollment_id).first()


def get_class_enrollment(db: Session, class_id: str, student_id: str) -> Optional[ClassEnrollment]:
    return (
        db.query(ClassEnrollment)
        .filter(ClassEnrollment.class_id == class_id, ClassEnrollment.student_id == student_id)
        .first()
    )


def is_student_user(db: Session, user_id: str) -> bool:
    sql = text(
        """
        SELECT COUNT(*) AS total
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        WHERE ur.user_id = :user_id
          AND r.role_code = 'student'
        """
    )
    return int(db.execute(sql, {"user_id": user_id}).scalar() or 0) > 0


def recount_class_students(db: Session, class_id: str) -> int:
    active_count = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES))
        .scalar()
    ) or 0

    clazz = get_class_by_id(db, class_id)
    if clazz:
        clazz.current_students = int(active_count)
        if hasattr(clazz, "updated_at"):
            clazz.updated_at = _now()
    return int(active_count)


def _active_count(db: Session, class_id: str) -> int:
    return int(
        (
            db.query(func.count(ClassEnrollment.id))
            .filter(ClassEnrollment.class_id == class_id)
            .filter(ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES))
            .scalar()
        )
        or 0
    )


def _ensure_class_capacity(db: Session, clazz: Class, old_status: str | None = None, new_status: str = "active") -> None:
    old_status = _normalize_status(old_status, default="")
    new_status = _normalize_status(new_status, default="active")
    old_is_active = old_status in ACTIVE_CLASS_ENROLLMENT_STATUSES
    new_is_active = new_status in ACTIVE_CLASS_ENROLLMENT_STATUSES

    if old_is_active or not new_is_active:
        return

    max_students = int(clazz.max_students or 0)
    if max_students > 0 and _active_count(db, clazz.id) >= max_students:
        raise ValueError("Lớp đã đủ sĩ số tối đa.")


def get_all_enrollments(db: Session, class_id: Optional[str] = None):
    query = db.query(ClassEnrollment)
    if class_id:
        query = query.filter(ClassEnrollment.class_id == class_id)
    return query.order_by(ClassEnrollment.created_at.desc()).all()


def get_pending_enrollments(db: Session, class_id: Optional[str] = None):
    query = db.query(ClassEnrollment).filter(ClassEnrollment.enrollment_status == "applied")
    if class_id:
        query = query.filter(ClassEnrollment.class_id == class_id)
    return query.order_by(ClassEnrollment.created_at.desc()).all()


def add_student_to_class(
    db: Session,
    class_id: str,
    user_id: str,
    enrollment_status: str = "active",
    approved_by: str | None = None,
    note: str | None = None,
):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Không tìm thấy sinh viên.")

    if not is_student_user(db, user_id):
        raise ValueError("Tài khoản được chọn không phải là sinh viên.")

    if getattr(user, "deleted_at", None):
        raise ValueError("Tài khoản sinh viên đã bị xóa.")

    enrollment_status = _normalize_status(enrollment_status, default="active")
    if enrollment_status not in ALLOWED_CLASS_ENROLLMENT_STATUSES:
        raise ValueError("Trạng thái ghi danh không hợp lệ.")

    existing = get_class_enrollment(db, class_id, user_id)
    old_status = (existing.enrollment_status if existing else "") or ""
    _ensure_class_capacity(db, clazz, old_status=old_status, new_status=enrollment_status)
    now = _now()

    try:
        if existing:
            if old_status in ACTIVE_CLASS_ENROLLMENT_STATUSES and enrollment_status in ACTIVE_CLASS_ENROLLMENT_STATUSES:
                raise ValueError("Sinh viên đã có trong lớp.")
            enrollment = existing
            enrollment.enrollment_status = enrollment_status
            if note:
                enrollment.note = note
        else:
            enrollment = ClassEnrollment(
                id=str(uuid.uuid4()),
                class_id=class_id,
                student_id=user_id,
                enrollment_status=enrollment_status,
                applied_at=now,
                note=note,
                created_at=now,
                updated_at=now,
            )
            db.add(enrollment)

        enrollment.updated_at = now
        if enrollment_status in ACTIVE_CLASS_ENROLLMENT_STATUSES:
            enrollment.approved_at = enrollment.approved_at or now
            enrollment.approved_by = approved_by or enrollment.approved_by
            enrollment.joined_at = enrollment.joined_at or now
            enrollment.left_at = None
        elif enrollment_status == "applied":
            enrollment.approved_at = None
            enrollment.approved_by = None
            enrollment.joined_at = None
            enrollment.left_at = None
        elif enrollment_status in {"rejected", "removed", "cancelled"}:
            enrollment.left_at = now
            enrollment.approved_by = approved_by or enrollment.approved_by
        elif enrollment_status == "completed":
            enrollment.left_at = now

        db.flush()
        recount_class_students(db, class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except ValueError:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi thêm sinh viên vào lớp: {str(e)}") from e


def remove_student_from_class(db: Session, class_id: str, user_id: str, approved_by: str | None = None):
    enrollment = get_class_enrollment(db, class_id, user_id)
    if not enrollment:
        raise ValueError("Không tìm thấy bản ghi ghi danh lớp học.")
    return update_enrollment_status(db=db, enrollment_id=enrollment.id, new_status="removed", approved_by=approved_by)


def add_enrollment(db: Session, class_id: str, user_id: str, enrollment_type: str | None = None, approved_by: str | None = None):
    note = f"Loại ghi danh: {enrollment_type}" if enrollment_type else None
    return add_student_to_class(db=db, class_id=class_id, user_id=user_id, enrollment_status="active", approved_by=approved_by, note=note)


def delete_enrollment(db: Session, enrollment_id: str, approved_by: str | None = None):
    return update_enrollment_status(db=db, enrollment_id=enrollment_id, new_status="removed", approved_by=approved_by)


def approve_enrollment(db: Session, enrollment_id: str, approved_by: str | None = None):
    return update_enrollment_status(db=db, enrollment_id=enrollment_id, new_status="approved", approved_by=approved_by)


def reject_enrollment(db: Session, enrollment_id: str, approved_by: str | None = None):
    return update_enrollment_status(db=db, enrollment_id=enrollment_id, new_status="rejected", approved_by=approved_by)


def update_enrollment_status(
    db: Session,
    enrollment_id: str,
    new_status: str | None = None,
    status: str | None = None,
    approved_by: str | None = None,
):
    enrollment = get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError("Không tìm thấy yêu cầu ghi danh.")

    target_status = _normalize_status(new_status or status, default="")
    if target_status not in ALLOWED_CLASS_ENROLLMENT_STATUSES:
        raise ValueError("Trạng thái ghi danh không hợp lệ.")

    clazz = get_class_by_id(db, enrollment.class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    old_status = _normalize_status(enrollment.enrollment_status, default="")
    _ensure_class_capacity(db, clazz, old_status=old_status, new_status=target_status)
    now = _now()

    try:
        enrollment.enrollment_status = target_status
        enrollment.updated_at = now
        if target_status in ACTIVE_CLASS_ENROLLMENT_STATUSES:
            enrollment.approved_at = enrollment.approved_at or now
            enrollment.approved_by = approved_by or enrollment.approved_by
            enrollment.joined_at = enrollment.joined_at or now
            enrollment.left_at = None
        elif target_status == "applied":
            enrollment.approved_at = None
            enrollment.approved_by = None
            enrollment.joined_at = None
            enrollment.left_at = None
        elif target_status in {"rejected", "removed", "cancelled"}:
            enrollment.left_at = now
            enrollment.approved_by = approved_by or enrollment.approved_by
        elif target_status == "completed":
            enrollment.left_at = now

        db.flush()
        recount_class_students(db, enrollment.class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except ValueError:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật trạng thái ghi danh: {str(e)}") from e
