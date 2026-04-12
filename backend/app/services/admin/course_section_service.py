import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.course import Course
from app.models.course_section import CourseSection


def get_section_by_id(db: Session, section_id: str):
    return db.query(CourseSection).filter(CourseSection.id == section_id).first()


def get_section_by_code(db: Session, section_code: str):
    return db.query(CourseSection).filter(CourseSection.section_code == section_code).first()


def get_all_sections(db: Session):
    try:
        return (
            db.query(CourseSection)
            .order_by(CourseSection.section_code.asc())
            .all()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi truy vấn học phần: {str(e)}") from e


def _validate_section_payload(
    db: Session,
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int,
    section_id: str | None = None,
):
    section_code = (section_code or "").strip()
    section_name = (section_name or "").strip()
    course_id = (course_id or "").strip()

    if not section_code:
        raise ValueError("Mã học phần không được để trống.")

    if not section_name:
        raise ValueError("Tên học phần không được để trống.")

    if not course_id:
        raise ValueError("Bạn phải chọn khóa học.")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Khóa học không tồn tại.")

    if max_students is None or int(max_students) <= 0:
        raise ValueError("Số lượng tối đa phải lớn hơn 0.")

    existing = get_section_by_code(db, section_code)
    if existing and existing.id != section_id:
        raise ValueError("Mã học phần đã tồn tại.")

    return section_code, section_name, course_id, int(max_students)


def create_section(
    db: Session,
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int = 50,
    location: str = "",
    schedule_info: str = "",
):
    try:
        section_code, section_name, course_id, max_students = _validate_section_payload(
            db=db,
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
        )

        new_section = CourseSection(
            id=str(uuid.uuid4()),
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            current_students=0,
            location=location.strip() if location else None,
            schedule_info=schedule_info.strip() if schedule_info else None,
        )

        db.add(new_section)
        db.commit()
        db.refresh(new_section)
        return new_section

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Dữ liệu học phần bị trùng hoặc không hợp lệ.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo học phần: {str(e)}") from e


def update_section(
    db: Session,
    section_id: str,
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int = 50,
    location: str = "",
    schedule_info: str = "",
):
    section = get_section_by_id(db, section_id)
    if not section:
        raise ValueError("Không tìm thấy học phần cần cập nhật.")

    try:
        section_code, section_name, course_id, max_students = _validate_section_payload(
            db=db,
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            section_id=section_id,
        )

        current_students = getattr(section, "current_students", 0) or 0
        if max_students < current_students:
            raise ValueError("Số lượng tối đa không được nhỏ hơn số sinh viên hiện tại.")

        section.section_code = section_code
        section.section_name = section_name
        section.course_id = course_id
        section.max_students = max_students
        section.location = location.strip() if location else None
        section.schedule_info = schedule_info.strip() if schedule_info else None

        db.commit()
        db.refresh(section)
        return section

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Dữ liệu học phần bị trùng hoặc không hợp lệ.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật học phần: {str(e)}") from e


def delete_section(db: Session, section_id: str):
    section = get_section_by_id(db, section_id)
    if not section:
        raise ValueError("Không tìm thấy học phần để xóa.")

    try:
        db.delete(section)
        db.commit()
        return True
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Không thể xóa học phần vì đang có dữ liệu liên kết.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa học phần: {str(e)}") from e