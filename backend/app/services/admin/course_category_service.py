from datetime import datetime
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.course_category import CourseCategory


def _normalize_name(category_name: str) -> str:
    name = (category_name or "").strip()
    if not name:
        raise ValueError("Tên danh mục không được để trống.")
    return name


def get_all_course_categories(db: Session):
    return db.query(CourseCategory).order_by(CourseCategory.category_name.asc()).all()


def get_course_category_by_id(category_id: str, db: Session):
    return db.query(CourseCategory).filter(CourseCategory.id == category_id).first()


def get_course_category_by_name(category_name: str, db: Session):
    return (
        db.query(CourseCategory)
        .filter(CourseCategory.category_name == category_name)
        .first()
    )


def create_course_category(db: Session, category_name: str, description: str | None):
    try:
        category_name = _normalize_name(category_name)
        description = (description or "").strip() or None

        existing = get_course_category_by_name(category_name, db)
        if existing:
            raise ValueError(f"Danh mục '{category_name}' đã tồn tại.")

        new_category = CourseCategory(
            id=str(uuid.uuid4()),
            category_name=category_name,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Tên danh mục đã tồn tại trong cơ sở dữ liệu.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi thêm danh mục khóa học: {str(e)}") from e


def update_course_category(db: Session, category_id: str, category_name: str, description: str | None):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise ValueError("Không tìm thấy danh mục để cập nhật.")

    try:
        category_name = _normalize_name(category_name)
        description = (description or "").strip() or None

        existing = (
            db.query(CourseCategory)
            .filter(
                CourseCategory.category_name == category_name,
                CourseCategory.id != category_id,
            )
            .first()
        )
        if existing:
            raise ValueError(f"Tên danh mục '{category_name}' đã tồn tại.")

        category.category_name = category_name
        category.description = description
        category.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(category)
        return category

    except ValueError:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Tên danh mục đã tồn tại trong cơ sở dữ liệu.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật danh mục: {str(e)}") from e


def delete_course_category(db: Session, category_id: str):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise ValueError("Không tìm thấy danh mục để xóa.")

    try:
        db.delete(category)
        db.commit()
        return True
    except IntegrityError as e:
        db.rollback()
        raise ValueError("Không thể xóa danh mục vì đang có khóa học liên kết.") from e
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa danh mục: {str(e)}") from e