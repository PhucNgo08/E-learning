from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.course_category import CourseCategory
import uuid

# =====================================================
# ➕ CREATE
# =====================================================
def create_category(category_name: str, description: str, db: Session):
    """Tạo danh mục khóa học mới"""
    try:
        # Kiểm tra trùng tên
        existing = db.query(CourseCategory).filter(
            CourseCategory.category_name == category_name
        ).first()
        if existing:
            raise ValueError(f"Danh mục '{category_name}' đã tồn tại.")

        new_category = CourseCategory(
            id=str(uuid.uuid4()),
            category_name=category_name,
            description=description,
        )
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category
    except ValueError as ve:
        db.rollback()
        raise RuntimeError(str(ve))
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi thêm danh mục khóa học: {str(e)}")


# =====================================================
# ✏️ UPDATE
# =====================================================
def update_category(category_id: str, category_name: str, description: str, db: Session):
    """Cập nhật danh mục khóa học"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise RuntimeError("Không tìm thấy danh mục để cập nhật.")

    try:
        # Kiểm tra trùng tên (trừ chính nó)
        existing = db.query(CourseCategory).filter(
            CourseCategory.category_name == category_name,
            CourseCategory.id != category_id
        ).first()
        if existing:
            raise ValueError(f"Tên danh mục '{category_name}' đã tồn tại.")

        category.category_name = category_name
        category.description = description
        db.commit()
        db.refresh(category)
        return category
    except ValueError as ve:
        db.rollback()
        raise RuntimeError(str(ve))
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật danh mục: {str(e)}")


# =====================================================
# ❌ DELETE
# =====================================================
def delete_category(category_id: str, db: Session):
    """Xóa danh mục khóa học"""
    category = db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
    if not category:
        raise RuntimeError("Không tìm thấy danh mục để xóa.")

    try:
        db.delete(category)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa danh mục: {str(e)}")


# =====================================================
# 📋 READ
# =====================================================
def get_all_categories(db: Session):
    """Lấy tất cả danh mục"""
    return db.query(CourseCategory).order_by(CourseCategory.category_name.asc()).all()


def get_category_by_id(category_id: str, db: Session):
    """Lấy danh mục theo ID"""
    return db.query(CourseCategory).filter(CourseCategory.id == category_id).first()
