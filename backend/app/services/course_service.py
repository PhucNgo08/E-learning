from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.course import Course
import uuid


def create_course(title: str, description: str, category_id: str, instructor_id: str, db: Session):
    """Tạo khóa học mới"""
    try:
        new_course = Course(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            category_id=category_id,
            instructor_id=instructor_id
        )
        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        return new_course
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo khóa học: {str(e)}")


def get_all_courses(db: Session):
    """Lấy danh sách khóa học"""
    return db.query(Course).all()


def update_course(course_id: str, title: str, description: str, category_id: str, db: Session):
    """Cập nhật khóa học"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Không tìm thấy khóa học.")
    try:
        course.title = title
        course.description = description
        course.category_id = category_id
        db.commit()
        db.refresh(course)
        return course
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật khóa học: {str(e)}")


def delete_course(course_id: str, db: Session):
    """Xóa khóa học"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Không tìm thấy khóa học.")
    try:
        db.delete(course)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa khóa học: {str(e)}")
