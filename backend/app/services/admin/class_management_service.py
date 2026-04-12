from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.class_enrollment import ClassEnrollment
from app.models.user import User
from app.services.admin.enrollment_management_service import (
    add_student_to_class as enrollment_add_student_to_class,
    remove_student_from_class as enrollment_remove_student_from_class,
)

ACTIVE_CLASS_ENROLLMENT_STATUSES = {"active", "approved"}
VALID_CLASS_TYPES = {"official", "club", "course", "temporary"}
VALID_CLASS_STATUSES = {"planning", "open_for_enrollment", "active", "completed", "cancelled"}


def get_all_classes(db: Session):
    return db.query(Class).order_by(Class.created_at.desc()).all()


def get_class_by_id(db: Session, class_id: str) -> Optional[Class]:
    return db.query(Class).filter(Class.id == class_id).first()


def get_class_by_code(db: Session, class_code: str) -> Optional[Class]:
    return db.query(Class).filter(Class.class_code == class_code).first()


def _validate_class_payload(
    db: Session,
    class_code: str,
    class_name: str,
    class_type: str,
    status: str,
    max_students: int,
    class_id: Optional[str] = None,
):
    class_code = (class_code or "").strip()
    class_name = (class_name or "").strip()
    class_type = (class_type or "official").strip()
    status = (status or "planning").strip()

    if not class_code:
        raise ValueError("Mã lớp không được để trống.")

    if not class_name:
        raise ValueError("Tên lớp không được để trống.")

    if class_type not in VALID_CLASS_TYPES:
        raise ValueError("Loại lớp không hợp lệ.")

    if status not in VALID_CLASS_STATUSES:
        raise ValueError("Trạng thái lớp không hợp lệ.")

    if max_students is None or int(max_students) <= 0:
        raise ValueError("Sĩ số tối đa phải lớn hơn 0.")

    existing = get_class_by_code(db, class_code)
    if existing and existing.id != class_id:
        raise ValueError("Mã lớp đã tồn tại.")

    return class_code, class_name, class_type, status, int(max_students)


def create_class(
    db: Session,
    class_code: str,
    class_name: str,
    class_type: str,
    academic_year_id: str,
    major_id: str,
    grade_level: int,
    max_students: int,
    homeroom_teacher_id: str,
    start_date=None,
    end_date=None,
    enrollment_start=None,
    enrollment_end=None,
    status: str = "planning",
):
    class_code, class_name, class_type, status, max_students = _validate_class_payload(
        db=db,
        class_code=class_code,
        class_name=class_name,
        class_type=class_type,
        status=status,
        max_students=max_students,
    )

    if start_date and end_date and start_date > end_date:
        raise ValueError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")

    if enrollment_start and enrollment_end and enrollment_start > enrollment_end:
        raise ValueError("Ngày mở ghi danh phải nhỏ hơn hoặc bằng ngày đóng ghi danh.")

    new_class = Class(
        class_code=class_code,
        class_name=class_name,
        class_type=class_type,
        academic_year_id=academic_year_id or None,
        major_id=major_id or None,
        grade_level=grade_level,
        max_students=max_students,
        current_students=0,
        homeroom_teacher_id=homeroom_teacher_id or None,
        start_date=start_date,
        end_date=end_date,
        enrollment_start=enrollment_start,
        enrollment_end=enrollment_end,
        status=status,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        return new_class
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Dữ liệu lớp học bị trùng hoặc không hợp lệ.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo lớp học: {str(e)}") from e


def update_class(db: Session, class_id: str, data: dict):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    class_code = data.get("class_code", clazz.class_code)
    class_name = data.get("class_name", clazz.class_name)
    class_type = data.get("class_type", clazz.class_type)
    status = data.get("status", clazz.status)
    max_students = data.get("max_students", clazz.max_students)

    class_code, class_name, class_type, status, max_students = _validate_class_payload(
        db=db,
        class_code=class_code,
        class_name=class_name,
        class_type=class_type,
        status=status,
        max_students=max_students,
        class_id=class_id,
    )

    start_date = data.get("start_date", clazz.start_date)
    end_date = data.get("end_date", clazz.end_date)
    enrollment_start = data.get("enrollment_start", clazz.enrollment_start)
    enrollment_end = data.get("enrollment_end", clazz.enrollment_end)

    if start_date and end_date and start_date > end_date:
        raise ValueError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")

    if enrollment_start and enrollment_end and enrollment_start > enrollment_end:
        raise ValueError("Ngày mở ghi danh phải nhỏ hơn hoặc bằng ngày đóng ghi danh.")

    active_students = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES))
        .scalar()
    )

    if int(max_students) < int(active_students or 0):
        raise ValueError("Sĩ số tối đa không được nhỏ hơn số sinh viên đang hoạt động.")

    try:
        clazz.class_code = class_code
        clazz.class_name = class_name
        clazz.class_type = class_type
        clazz.status = status
        clazz.academic_year_id = data.get("academic_year_id") or None
        clazz.major_id = data.get("major_id") or None
        clazz.homeroom_teacher_id = data.get("homeroom_teacher_id") or None
        clazz.grade_level = data.get("grade_level")
        clazz.max_students = max_students
        clazz.start_date = start_date
        clazz.end_date = end_date
        clazz.enrollment_start = enrollment_start
        clazz.enrollment_end = enrollment_end
        clazz.current_students = int(active_students or 0)
        clazz.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(clazz)
        return clazz
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Dữ liệu lớp học bị trùng hoặc không hợp lệ.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật lớp học: {str(e)}") from e


def delete_class(db: Session, class_id: str):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học.")

    try:
        db.delete(clazz)
        db.commit()
        return True
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Không thể xóa lớp học vì đang có dữ liệu liên kết.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa lớp học: {str(e)}") from e


def get_students_in_class(db: Session, class_id: str):
    return (
        db.query(User)
        .join(ClassEnrollment, ClassEnrollment.student_id == User.id)
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status.in_(list(ACTIVE_CLASS_ENROLLMENT_STATUSES)))
        .all()
    )


def add_student_to_class(db: Session, class_id: str, user_id: str):
    return enrollment_add_student_to_class(db, class_id, user_id)


def remove_student_from_class(db: Session, class_id: str, user_id: str):
    return enrollment_remove_student_from_class(db, class_id, user_id)


def get_pending_enrollments(db: Session, class_id: str):
    return (
        db.query(ClassEnrollment)
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status == "applied")
        .all()
    )


def get_class_statistics(db: Session, class_id: str):
    total = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .scalar()
    )
    active = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status.in_(list(ACTIVE_CLASS_ENROLLMENT_STATUSES)))
        .scalar()
    )
    pending = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status == "applied")
        .scalar()
    )
    rejected = (
        db.query(func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_id == class_id)
        .filter(ClassEnrollment.enrollment_status == "rejected")
        .scalar()
    )

    return {
        "total_enrollments": total or 0,
        "active_students": active or 0,
        "pending_requests": pending or 0,
        "rejected_requests": rejected or 0,
    }