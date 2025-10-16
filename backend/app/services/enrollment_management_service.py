from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.enrollment import Enrollment
from datetime import datetime
import uuid

# 🧩 Tạo ghi danh mới
def add_enrollment(user_id: str, class_id: str, enrollment_type: str, db: Session):
    try:
        existing = db.query(Enrollment).filter(
            Enrollment.user_id == user_id, Enrollment.class_id == class_id
        ).first()
        if existing:
            raise ValueError("Học viên đã ghi danh vào lớp này.")
        enrollment = Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            class_id=class_id,
            enrollment_type=enrollment_type,
            enrollment_status="applied",
            applied_at=datetime.utcnow(),
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi ghi danh: {str(e)}")


# 📋 Lấy danh sách ghi danh theo học viên
def get_enrollments_by_user(user_id: str, db: Session):
    try:
        return db.query(Enrollment).filter(Enrollment.user_id == user_id).all()
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách ghi danh: {str(e)}")


# ✏️ Cập nhật trạng thái ghi danh
def update_enrollment_status(enrollment_id: str, new_status: str, db: Session):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise ValueError("Không tìm thấy ghi danh này.")
    try:
        enrollment.enrollment_status = new_status
        enrollment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(enrollment)
        return enrollment
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật ghi danh: {str(e)}")


# ❌ Xóa ghi danh
def delete_enrollment(enrollment_id: str, db: Session):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise ValueError("Không tìm thấy ghi danh để xóa.")
    try:
        db.delete(enrollment)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa ghi danh: {str(e)}")
