from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.course_section import CourseSection
import uuid


def create_section(
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int,
    location: str,
    schedule_info: str,
    db: Session,
):
    """Tạo học phần mới"""
    try:
        new_section = CourseSection(
            id=str(uuid.uuid4()),
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            location=location,
            schedule_info=schedule_info,
        )
        db.add(new_section)
        db.commit()
        db.refresh(new_section)
        return new_section
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo học phần: {str(e)}")


def get_all_sections(db: Session):
    """Lấy tất cả học phần"""
    try:
        return db.query(CourseSection).order_by(CourseSection.section_code).all()
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi truy vấn phần học: {str(e)}")


def update_section(
    section_id: str,
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int,
    location: str,
    schedule_info: str,
    db: Session,
):
    """Cập nhật phần học"""
    section = db.query(CourseSection).filter(CourseSection.id == section_id).first()
    if not section:
        raise ValueError("Không tìm thấy phần học.")

    try:
        section.section_code = section_code
        section.section_name = section_name
        section.course_id = course_id
        section.max_students = max_students
        section.location = location
        section.schedule_info = schedule_info
        db.commit()
        db.refresh(section)
        return section
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật phần học: {str(e)}")


def delete_section(section_id: str, db: Session):
    """Xóa phần học"""
    section = db.query(CourseSection).filter(CourseSection.id == section_id).first()
    if not section:
        raise ValueError("Không tìm thấy phần học.")
    try:
        db.delete(section)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa phần học: {str(e)}")
