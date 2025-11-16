"""
=========================================================
📘 class_management_service.py
Quản lý LỚP HỌC + ENROLLMENT (Admin + Teacher)
=========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.models.classes import Class
from app.models.enrollment import Enrollment
from app.models.user import User


# ==========================================================
# 1️⃣ LẤY DANH SÁCH LỚP
# ==========================================================
def get_all_classes(db: Session):
    return (
        db.query(Class)
        .order_by(Class.created_at.desc())
        .all()
    )


# ==========================================================
# 2️⃣ LẤY THÔNG TIN 1 LỚP
# ==========================================================
def get_class_by_id(db: Session, class_id: str):
    return db.query(Class).filter(Class.id == class_id).first()


# ==========================================================
# 3️⃣ TẠO LỚP MỚI
# ==========================================================
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
):
    new_class = Class(
        class_code=class_code,
        class_name=class_name,
        class_type=class_type,
        academic_year_id=academic_year_id,
        major_id=major_id,
        grade_level=grade_level,
        max_students=max_students,
        homeroom_teacher_id=homeroom_teacher_id,
        start_date=start_date,
        end_date=end_date,
        enrollment_start=enrollment_start,
        enrollment_end=enrollment_end,
        status="planning",
    )

    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


# ==========================================================
# 4️⃣ CẬP NHẬT LỚP
# ==========================================================
def update_class(db: Session, class_id: str, data: dict):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        return None

    for field, value in data.items():
        setattr(clazz, field, value)

    clazz.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(clazz)
    return clazz


# ==========================================================
# 5️⃣ XÓA LỚP (kèm enrollment cascade)
# ==========================================================
def delete_class(db: Session, class_id: str):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        return None

    db.delete(clazz)
    db.commit()
    return True


# ==========================================================
# 6️⃣ LẤY TẤT CẢ HỌC SINH TRONG LỚP
# ==========================================================
def get_students_in_class(db: Session, class_id: str):
    return (
        db.query(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.class_id == class_id)
        .filter(Enrollment.enrollment_status.in_(["active", "approved"]))
        .all()
    )


# ==========================================================
# 7️⃣ THÊM SINH VIÊN VÀO LỚP (Admin thêm trực tiếp)
# ==========================================================
def add_student_to_class(db: Session, class_id: str, user_id: str):

    clazz = get_class_by_id(db, class_id)
    if not clazz:
        return None, "Class not found"

    # Kiểm tra trùng
    exists = (
        db.query(Enrollment)
        .filter_by(class_id=class_id, user_id=user_id)
        .first()
    )
    if exists:
        return None, "Student already enrolled"

    # Kiểm tra max
    if clazz.current_students >= clazz.max_students:
        return None, "Class is full"

    enrollment = Enrollment(
        user_id=user_id,
        class_id=class_id,
        enrollment_type="official",
        enrollment_status="active",
        approved_at=datetime.utcnow(),
        enrolled_at=datetime.utcnow(),
    )

    clazz.current_students += 1

    db.add(enrollment)
    db.commit()
    return enrollment, None


# ==========================================================
# 8️⃣ XÓA SINH VIÊN KHỎI LỚP
# ==========================================================
def remove_student_from_class(db: Session, class_id: str, user_id: str):
    enrollment = (
        db.query(Enrollment)
        .filter_by(class_id=class_id, user_id=user_id)
        .first()
    )

    if not enrollment:
        return None

    clazz = get_class_by_id(db, class_id)
    if clazz and clazz.current_students > 0:
        clazz.current_students -= 1

    db.delete(enrollment)
    db.commit()
    return True


# ==========================================================
# 9️⃣ LẤY DANH SÁCH ENROLLMENT ĐANG CHỜ DUYỆT
# ==========================================================
def get_pending_enrollments(db: Session, class_id: str):
    return (
        db.query(Enrollment)
        .filter(Enrollment.class_id == class_id)
        .filter(Enrollment.enrollment_status == "applied")
        .all()
    )


# ==========================================================
# 🔟 DUYỆT ENROLLMENT
# ==========================================================
def approve_enrollment(db: Session, enrollment_id: str, admin_id: str):
    enrollment = db.query(Enrollment).filter_by(id=enrollment_id).first()
    if not enrollment:
        return None

    clazz = get_class_by_id(db, enrollment.class_id)
    if clazz.current_students >= clazz.max_students:
        return None  # full

    enrollment.enrollment_status = "active"
    enrollment.approved_by = admin_id
    enrollment.approved_at = datetime.utcnow()
    enrollment.enrolled_at = datetime.utcnow()

    clazz.current_students += 1

    db.commit()
    return enrollment


# ==========================================================
# 1️⃣1️⃣ TỪ CHỐI ENROLLMENT
# ==========================================================
def reject_enrollment(db: Session, enrollment_id: str, admin_id: str):
    enrollment = db.query(Enrollment).filter_by(id=enrollment_id).first()
    if not enrollment:
        return None

    enrollment.enrollment_status = "rejected"
    enrollment.approved_by = admin_id
    enrollment.approved_at = datetime.utcnow()

    db.commit()
    return enrollment


# ==========================================================
# 1️⃣2️⃣ DROPPING (SINH VIÊN RỜI LỚP)
# ==========================================================
def drop_student(db: Session, enrollment_id: str):
    enrollment = db.query(Enrollment).filter_by(id=enrollment_id).first()
    if not enrollment:
        return None

    clazz = get_class_by_id(db, enrollment.class_id)
    if clazz and clazz.current_students > 0:
        clazz.current_students -= 1

    db.delete(enrollment)
    db.commit()
    return True


# ==========================================================
# 1️⃣3️⃣ THỐNG KÊ LỚP
# ==========================================================
def get_class_statistics(db: Session, class_id: str):
    total = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.class_id == class_id)
        .scalar()
    )

    active = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.class_id == class_id)
        .filter(Enrollment.enrollment_status.in_(["active", "approved"]))
        .scalar()
    )

    pending = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.class_id == class_id)
        .filter(Enrollment.enrollment_status == "applied")
        .scalar()
    )

    rejected = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.class_id == class_id)
        .filter(Enrollment.enrollment_status == "rejected")
        .scalar()
    )

    return {
        "total_enrollments": total,
        "active_students": active,
        "pending_requests": pending,
        "rejected_requests": rejected,
    }
