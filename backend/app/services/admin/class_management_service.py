from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.classes import Class
from datetime import date
import uuid


# ============================================================
# 🧩 CREATE - Tạo lớp học mới
# ============================================================
def create_class(
    class_code: str,
    class_name: str,
    class_type: str,
    academic_year_id: str,
    major_id: str,
    homeroom_teacher_id: str,
    max_students: int,
    start_date: date,
    end_date: date,
    db: Session
):
    """
    ✅ Tạo lớp học mới (dùng trong form create.html)
    """
    try:
        # ⚙️ Kiểm tra trùng mã lớp
        existing = db.query(Class).filter(Class.class_code == class_code).first()
        if existing:
            raise ValueError(f"Mã lớp '{class_code}' đã tồn tại trong hệ thống.")

        new_class = Class(
            id=str(uuid.uuid4()),
            class_code=class_code.strip(),
            class_name=class_name.strip(),
            class_type=class_type,
            academic_year_id=academic_year_id or None,
            major_id=major_id or None,
            homeroom_teacher_id=homeroom_teacher_id or None,
            max_students=max_students or 50,
            current_students=0,
            status="planning",
            start_date=start_date,
            end_date=end_date,
        )

        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        return new_class

    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo lớp học: {str(e)}")


# ============================================================
# 📋 READ - Lấy danh sách lớp học
# ============================================================
def get_all_classes(db: Session):
    """
    ✅ Lấy danh sách tất cả lớp học (dùng cho manage.html)
    """
    try:
        return db.query(Class).order_by(Class.created_at.desc()).all()
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách lớp học: {str(e)}")


def get_class_by_id(class_id: str, db: Session):
    """
    ✅ Lấy lớp học theo ID (dùng cho edit.html hoặc delete.html)
    """
    try:
        return db.query(Class).filter(Class.id == class_id).first()
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi tìm lớp học: {str(e)}")


# ============================================================
# ✏️ UPDATE - Cập nhật thông tin lớp học
# ============================================================
def update_class(
    class_id: str,
    class_code: str,
    class_name: str,
    class_type: str,
    academic_year_id: str,
    major_id: str,
    homeroom_teacher_id: str,
    max_students: int,
    status: str,
    start_date: date,
    end_date: date,
    db: Session
):
    """
    ✅ Cập nhật thông tin lớp học (sử dụng trong form edit.html)
    """
    clazz = get_class_by_id(class_id, db)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học để cập nhật.")

    try:
        clazz.class_code = class_code.strip()
        clazz.class_name = class_name.strip()
        clazz.class_type = class_type
        clazz.academic_year_id = academic_year_id or clazz.academic_year_id
        clazz.major_id = major_id or clazz.major_id
        clazz.homeroom_teacher_id = homeroom_teacher_id or clazz.homeroom_teacher_id
        clazz.max_students = max_students or clazz.max_students
        clazz.status = status or clazz.status
        clazz.start_date = start_date
        clazz.end_date = end_date

        db.commit()
        db.refresh(clazz)
        return clazz

    except (SQLAlchemyError, ValueError) as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật lớp học: {str(e)}")


# ============================================================
# ❌ DELETE - Xóa lớp học
# ============================================================
def delete_class(class_id: str, db: Session):
    """
    ✅ Xóa lớp học (sử dụng trong delete.html)
    """
    clazz = get_class_by_id(class_id, db)
    if not clazz:
        raise ValueError("Không tìm thấy lớp học để xóa.")

    try:
        db.delete(clazz)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa lớp học: {str(e)}")
