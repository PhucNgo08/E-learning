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
    grade_level: int,
    max_students: int,
    start_date: date,
    end_date: date,
    enrollment_start: date,
    enrollment_end: date,
    homeroom_teacher_id: str,
    db: Session
):
    try:
        new_class = Class(
            id=str(uuid.uuid4()),
            class_code=class_code,
            class_name=class_name,
            class_type=class_type,

            academic_year_id=academic_year_id,
            major_id=major_id,
            grade_level=grade_level,

            max_students=max_students or 50,
            current_students=0,

            start_date=start_date,
            end_date=end_date,
            enrollment_start=enrollment_start,
            enrollment_end=enrollment_end,

            homeroom_teacher_id=homeroom_teacher_id,
            status="planning",
        )

        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        return new_class

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo lớp học: {str(e)}")


# ============================================================
# 📋 READ - Lấy danh sách lớp học
# ============================================================
def get_all_classes(db: Session):
    return db.query(Class).order_by(Class.created_at.desc()).all()


# ============================================================
# ✏️ UPDATE - Cập nhật lớp học
# ============================================================
def update_class(
    class_id: str,
    class_code: str,
    class_name: str,
    class_type: str,
    academic_year_id: str,
    major_id: str,
    grade_level: int,
    max_students: int,
    start_date: date,
    end_date: date,
    enrollment_start: date,
    enrollment_end: date,
    homeroom_teacher_id: str,
    status: str,
    db: Session
):
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise ValueError("Không tìm thấy lớp học.")

    try:
        class_obj.class_code = class_code
        class_obj.class_name = class_name
        class_obj.class_type = class_type

        class_obj.academic_year_id = academic_year_id
        class_obj.major_id = major_id
        class_obj.grade_level = grade_level

        class_obj.max_students = max_students
        class_obj.start_date = start_date
        class_obj.end_date = end_date

        class_obj.enrollment_start = enrollment_start
        class_obj.enrollment_end = enrollment_end

        class_obj.homeroom_teacher_id = homeroom_teacher_id
        class_obj.status = status

        db.commit()
        db.refresh(class_obj)
        return class_obj

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật lớp học: {str(e)}")


# ============================================================
# ❌ DELETE - Xóa lớp học
# ============================================================
def delete_class(class_id: str, db: Session):
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise ValueError("Không tìm thấy lớp học.")

    try:
        db.delete(class_obj)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa lớp học: {str(e)}")
