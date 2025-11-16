from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import uuid

from app.models.enrollment import Enrollment
from app.models.classes import Class


# ============================================================
# 🧩 CREATE - Thêm ghi danh
# ============================================================
def add_enrollment(
    user_id: str,
    class_id: str,
    enrollment_type: str,
    db: Session,
    course_id: str = None,
):
    try:
        # Kiểm tra ghi danh trùng
        existing = db.query(Enrollment).filter(
            Enrollment.user_id == user_id,
            Enrollment.class_id == class_id,
        ).first()

        if existing:
            raise ValueError("Học viên đã ghi danh vào lớp này.")

        enrollment = Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            class_id=class_id,
            course_id=course_id,
            enrollment_type=enrollment_type,
            enrollment_status="applied",  # trạng thái mặc định
            applied_at=datetime.utcnow(),
        )

        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi ghi danh: {str(e)}")


# ============================================================
# 📋 GET - Danh sách ghi danh theo học viên
# ============================================================
def get_enrollments_by_user(user_id: str, db: Session):
    try:
        return db.query(Enrollment).filter(
            Enrollment.user_id == user_id
        ).all()
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách ghi danh: {str(e)}")


# ============================================================
# ✏️ UPDATE - Cập nhật trạng thái chung
# ============================================================
def update_enrollment_status(enrollment_id: str, new_status: str, db: Session, approved_by: str = None):
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id
    ).first()

    if not enrollment:
        raise ValueError("Không tìm thấy ghi danh này.")

    try:
        enrollment.enrollment_status = new_status
        enrollment.updated_at = datetime.utcnow()

        # Nếu duyệt
        if new_status == "approved":
            enrollment.approved_by = approved_by
            enrollment.approved_at = datetime.utcnow()

        # Nếu kích hoạt
        if new_status == "active":
            enrollment.enrolled_at = datetime.utcnow()

        # Nếu hoàn thành
        if new_status == "completed":
            enrollment.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(enrollment)
        return enrollment

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật ghi danh: {str(e)}")


# ============================================================
# 👍 APPROVE - Phê duyệt ghi danh (Chuẩn workflow)
# ============================================================
def approve_enrollment(enrollment_id: str, approved_by: str, db: Session):
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id
    ).first()

    if not enrollment:
        raise ValueError("Không tìm thấy đơn ghi danh.")

    # Tìm lớp tương ứng
    cls = db.query(Class).filter(Class.id == enrollment.class_id).first()
    if not cls:
        raise ValueError("Không tìm thấy lớp học.")

    # Kiểm tra sĩ số
    if cls.current_students is not None and cls.max_students is not None:
        if cls.current_students >= cls.max_students:
            raise ValueError("Không thể duyệt — Lớp đã đủ sĩ số.")

    try:
        # Cập nhật trạng thái ghi danh
        enrollment.enrollment_status = "approved"
        enrollment.approved_by = approved_by
        enrollment.approved_at = datetime.utcnow()
        enrollment.updated_at = datetime.utcnow()

        # Tăng sĩ số lớp
        cls.current_students += 1
        cls.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(enrollment)
        return enrollment

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi phê duyệt ghi danh: {str(e)}")


# ============================================================
# ❌ REJECT - Từ chối ghi danh
# ============================================================
def reject_enrollment(enrollment_id: str, approved_by: str, db: Session):
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id
    ).first()

    if not enrollment:
        raise ValueError("Không tìm thấy đơn ghi danh.")

    try:
        enrollment.enrollment_status = "rejected"
        enrollment.approved_by = approved_by
        enrollment.approved_at = datetime.utcnow()
        enrollment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(enrollment)
        return enrollment

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi từ chối ghi danh: {str(e)}")


# ============================================================
# ❌ DELETE - Xóa ghi danh
# ============================================================
def delete_enrollment(enrollment_id: str, db: Session):
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id
    ).first()

    if not enrollment:
        raise ValueError("Không tìm thấy ghi danh để xóa.")

    try:
        db.delete(enrollment)
        db.commit()
        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa ghi danh: {str(e)}")
