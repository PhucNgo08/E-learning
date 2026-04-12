import uuid

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.major import Major


def get_all_majors(db: Session, q: str | None = None):
    query = db.query(Major)

    if q and q.strip():
        keyword = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Major.major_code.ilike(keyword),
                Major.major_name.ilike(keyword),
                Major.faculty_name.ilike(keyword),
            )
        )

    return query.order_by(Major.major_name.asc()).all()


def get_major_by_id(db: Session, major_id: str):
    return db.query(Major).filter(Major.id == major_id).first()


def get_major_by_code(db: Session, major_code: str):
    return db.query(Major).filter(Major.major_code == major_code).first()


def _validate_major_payload(
    db: Session,
    major_code: str,
    major_name: str,
    faculty_name: str | None,
    major_id: str | None = None,
):
    major_code = (major_code or "").strip()
    major_name = (major_name or "").strip()
    faculty_name = (faculty_name or "").strip() or None

    if not major_code:
        raise ValueError("Mã ngành không được để trống.")

    if not major_name:
        raise ValueError("Tên ngành không được để trống.")

    existing = (
        db.query(Major)
        .filter(
            or_(
                Major.major_code == major_code,
                Major.major_name == major_name,
            )
        )
        .first()
    )

    if existing and existing.id != major_id:
        raise ValueError("Mã ngành hoặc tên ngành đã tồn tại trong hệ thống.")

    return major_code, major_name, faculty_name


def create_major(db: Session, major_code: str, major_name: str, faculty_name: str | None):
    try:
        major_code, major_name, faculty_name = _validate_major_payload(
            db=db,
            major_code=major_code,
            major_name=major_name,
            faculty_name=faculty_name,
        )

        new_major = Major(
            id=str(uuid.uuid4()),
            major_code=major_code,
            major_name=major_name,
            faculty_name=faculty_name,
            is_active=True,
        )

        db.add(new_major)
        db.commit()
        db.refresh(new_major)
        return new_major

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Mã ngành hoặc tên ngành đã tồn tại trong hệ thống.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo ngành học: {str(e)}") from e


def update_major(
    db: Session,
    major_id: str,
    major_code: str,
    major_name: str,
    faculty_name: str | None,
    is_active: bool,
):
    major = get_major_by_id(db, major_id)
    if not major:
        raise ValueError("Không tìm thấy ngành học.")

    try:
        major_code, major_name, faculty_name = _validate_major_payload(
            db=db,
            major_code=major_code,
            major_name=major_name,
            faculty_name=faculty_name,
            major_id=major_id,
        )

        major.major_code = major_code
        major.major_name = major_name
        major.faculty_name = faculty_name
        major.is_active = is_active

        db.commit()
        db.refresh(major)
        return major

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Mã ngành hoặc tên ngành đã tồn tại trong hệ thống.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật ngành học: {str(e)}") from e


def delete_major(db: Session, major_id: str):
    major = get_major_by_id(db, major_id)
    if not major:
        raise ValueError("Không tìm thấy ngành học.")

    try:
        db.delete(major)
        db.commit()
        return True
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Không thể xóa ngành học vì đang có dữ liệu liên kết.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa ngành học: {str(e)}") from e