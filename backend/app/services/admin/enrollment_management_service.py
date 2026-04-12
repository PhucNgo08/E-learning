from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.class_enrollment import ClassEnrollment
from app.models.user import User


ACTIVE_CLASS_ENROLLMENT_STATUSES = {"active", "approved"}


def get_class_by_id(db: Session, class_id: str) -> Optional[Class]:
    return db.query(Class).filter(Class.id == class_id).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_enrollment_by_id(db: Session, enrollment_id: str) -> Optional[ClassEnrollment]:
    return (
        db.query(ClassEnrollment)
        .filter(ClassEnrollment.id == enrollment_id)
        .first()
    )


def get_class_enrollment(
    db: Session,
    class_id: str,
    student_id: str,
) -> Optional[ClassEnrollment]:
    return (
        db.query(ClassEnrollment)
        .filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == student_id,
        )
        .first()
    )


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
        clazz.updated_at = datetime.utcnow()

    return int(active_count)


def get_all_enrollments(db: Session, class_id: Optional[str] = None):
    query = db.query(ClassEnrollment)
    if class_id:
        query = query.filter(ClassEnrollment.class_id == class_id)
    return query.order_by(ClassEnrollment.created_at.desc()).all()


def get_pending_enrollments(db: Session, class_id: Optional[str] = None):
    query = db.query(ClassEnrollment).filter(
        ClassEnrollment.enrollment_status == "applied"
    )
    if class_id:
        query = query.filter(ClassEnrollment.class_id == class_id)
    return query.order_by(ClassEnrollment.created_at.desc()).all()


def add_student_to_class(db: Session, class_id: str, user_id: str):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    user = get_user_by_id(db, user_id)
    if not user:
        raise ValueError("Không tìm thấy sinh viên.")

    existing = get_class_enrollment(db, class_id, user_id)

    active_count = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES))
        .scalar()
    ) or 0

    if existing:
        if existing.enrollment_status in ACTIVE_CLASS_ENROLLMENT_STATUSES:
            raise ValueError("Sinh viên đã có trong lớp.")

        if int(active_count) >= int(clazz.max_students or 0):
            raise ValueError("Lớp đã đủ sĩ số tối đa.")

        try:
            existing.enrollment_status = "active"
            existing.approved_at = datetime.utcnow()
            existing.joined_at = datetime.utcnow()
            existing.left_at = None
            existing.updated_at = datetime.utcnow()

            db.flush()
            recount_class_students(db, class_id)
            db.commit()
            db.refresh(existing)
            return existing
        except SQLAlchemyError as e:
            db.rollback()
            raise RuntimeError(f"Lỗi khi thêm sinh viên vào lớp: {str(e)}") from e

    if int(active_count) >= int(clazz.max_students or 0):
        raise ValueError("Lớp đã đủ sĩ số tối đa.")

    enrollment = ClassEnrollment(
        class_id=class_id,
        student_id=user_id,
        enrollment_status="active",
        applied_at=datetime.utcnow(),
        approved_at=datetime.utcnow(),
        joined_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        db.add(enrollment)
        db.flush()
        recount_class_students(db, class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi thêm sinh viên vào lớp: {str(e)}") from e


def remove_student_from_class(db: Session, class_id: str, user_id: str):
    enrollment = get_class_enrollment(db, class_id, user_id)
    if not enrollment:
        raise ValueError("Không tìm thấy bản ghi ghi danh lớp học.")

    try:
        enrollment.enrollment_status = "removed"
        enrollment.left_at = datetime.utcnow()
        enrollment.updated_at = datetime.utcnow()

        db.flush()
        recount_class_students(db, class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa sinh viên khỏi lớp: {str(e)}") from e


def add_enrollment(db: Session, class_id: str, user_id: str):
    return add_student_to_class(db, class_id, user_id)


def delete_enrollment(db: Session, enrollment_id: str):
    enrollment = get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError("Không tìm thấy bản ghi ghi danh.")

    try:
        enrollment.enrollment_status = "removed"
        enrollment.left_at = datetime.utcnow()
        enrollment.updated_at = datetime.utcnow()

        db.flush()
        recount_class_students(db, enrollment.class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa ghi danh: {str(e)}") from e


def approve_enrollment(db: Session, enrollment_id: str):
    enrollment = get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError("Không tìm thấy yêu cầu ghi danh.")

    clazz = get_class_by_id(db, enrollment.class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    active_count = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == enrollment.class_id)
        .filter(ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES))
        .scalar()
    ) or 0

    if enrollment.enrollment_status not in ACTIVE_CLASS_ENROLLMENT_STATUSES:
        if int(active_count) >= int(clazz.max_students or 0):
            raise ValueError("Lớp đã đủ sĩ số tối đa.")

    try:
        enrollment.enrollment_status = "approved"
        enrollment.approved_at = datetime.utcnow()
        enrollment.joined_at = enrollment.joined_at or datetime.utcnow()
        enrollment.left_at = None
        enrollment.updated_at = datetime.utcnow()

        db.flush()
        recount_class_students(db, enrollment.class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi duyệt ghi danh: {str(e)}") from e


def reject_enrollment(db: Session, enrollment_id: str):
    enrollment = get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError("Không tìm thấy yêu cầu ghi danh.")

    try:
        enrollment.enrollment_status = "rejected"
        enrollment.updated_at = datetime.utcnow()

        db.flush()
        recount_class_students(db, enrollment.class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi từ chối ghi danh: {str(e)}") from e


def update_enrollment_status(db: Session, enrollment_id: str, status: str):
    enrollment = get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError("Không tìm thấy yêu cầu ghi danh.")

    status = (status or "").strip().lower()
    allowed_statuses = {
        "applied",
        "approved",
        "active",
        "rejected",
        "removed",
        "cancelled",
        "completed",
    }

    if status not in allowed_statuses:
        raise ValueError("Trạng thái ghi danh không hợp lệ.")

    clazz = get_class_by_id(db, enrollment.class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    active_count = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == enrollment.class_id)
        .filter(ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES))
        .scalar()
    ) or 0

    old_status = (enrollment.enrollment_status or "").strip().lower()
    old_is_active = old_status in ACTIVE_CLASS_ENROLLMENT_STATUSES
    new_is_active = status in ACTIVE_CLASS_ENROLLMENT_STATUSES

    if not old_is_active and new_is_active:
        if int(active_count) >= int(clazz.max_students or 0):
            raise ValueError("Lớp đã đủ sĩ số tối đa.")

    try:
        enrollment.enrollment_status = status
        now = datetime.utcnow()

        if status in {"approved", "active"}:
            enrollment.approved_at = enrollment.approved_at or now
            enrollment.joined_at = enrollment.joined_at or now
            enrollment.left_at = None
        elif status in {"rejected", "removed", "cancelled"}:
            enrollment.left_at = now
        elif status == "applied":
            enrollment.approved_at = None
            enrollment.joined_at = None
            enrollment.left_at = None

        enrollment.updated_at = now

        db.flush()
        recount_class_students(db, enrollment.class_id)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật trạng thái ghi danh: {str(e)}") from e