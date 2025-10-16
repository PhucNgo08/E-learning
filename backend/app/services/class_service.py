from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.classes import Class
import uuid


def create_class(name: str, major_id: str, academic_year_id: str, db: Session):
    """Tạo lớp học mới"""
    try:
        new_class = Class(
            id=str(uuid.uuid4()),
            name=name,
            major_id=major_id,
            academic_year_id=academic_year_id
        )
        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        return new_class
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo lớp học: {str(e)}")


def get_all_classes(db: Session):
    """Lấy danh sách lớp học"""
    return db.query(Class).all()


def update_class(class_id: str, name: str, major_id: str, academic_year_id: str, db: Session):
    """Cập nhật lớp học"""
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise ValueError("Không tìm thấy lớp học.")
    try:
        class_obj.name = name
        class_obj.major_id = major_id
        class_obj.academic_year_id = academic_year_id
        db.commit()
        db.refresh(class_obj)
        return class_obj
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật lớp học: {str(e)}")


def delete_class(class_id: str, db: Session):
    """Xóa lớp học"""
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
