import uuid
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.module import Module
from app.models.course import Course


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


# =========================================================
# 🔒 Kiểm tra quyền sở hữu khóa học
# =========================================================
def _course_owned(db: Session, teacher_id: str, course_id: str):
    return (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )


# =========================================================
# 📋 Danh sách Module theo khóa học
# =========================================================
def list_modules_by_course(db: Session, course_id: str):
    return (
        db.query(Module)
        .filter(
            Module.course_id == course_id,
            Module.deleted_at.is_(None)
        )
        .order_by(Module.module_number.asc())
        .all()
    )


# =========================================================
# 📚 Danh sách tất cả module của giáo viên
# =========================================================
def list_all_modules_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(
            Course.teacher_id == teacher_id,
            Module.deleted_at.is_(None)
        )
        .order_by(Course.course_name.asc(), Module.module_number.asc())
        .all()
    )


# =========================================================
# ➕ Tạo Module mới
# =========================================================
def create_module(
    db: Session,
    teacher_id: str,
    course_id: str,
    module_number: int,
    title: str,
    description: str,
    learning_objectives: str,
):
    try:
        course = _course_owned(db, teacher_id, course_id)
        if not course:
            return {"error": "Bạn không có quyền tạo module cho khóa học này."}

        title = _clean_text(title)
        description = _clean_text(description)
        learning_objectives = _clean_text(learning_objectives)

        if not title:
            return {"error": "Tên chương không được để trống."}

        existed = (
            db.query(Module)
            .filter(
                Module.course_id == course_id,
                Module.module_number == module_number,
                Module.deleted_at.is_(None)
            )
            .first()
        )
        if existed:
            return {"error": "Thứ tự module đã tồn tại trong khóa học này."}

        new_module = Module(
            id=str(uuid.uuid4()),
            course_id=course_id,
            module_number=module_number,
            title=title,
            description=description,
            learning_objectives=learning_objectives,
            is_published=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_module)
        db.commit()
        db.refresh(new_module)
        return {"success": True, "module": new_module}

    except SQLAlchemyError:
        db.rollback()
        return {"error": "Đã xảy ra lỗi khi tạo module."}


# =========================================================
# 🔍 Lấy thông tin Module + kiểm tra quyền
# =========================================================
def get_module_owned_with_course(db: Session, teacher_id: str, module_id: str):
    module = (
        db.query(Module)
        .filter(
            Module.id == module_id,
            Module.deleted_at.is_(None)
        )
        .first()
    )
    if not module:
        return None, None

    course = _course_owned(db, teacher_id, module.course_id)
    if not course:
        return None, None

    return module, course


# =========================================================
# ✏️ Cập nhật Module
# =========================================================
def update_module(
    db: Session,
    teacher_id: str,
    module_id: str,
    module_number: int,
    title: str,
    description: str,
    learning_objectives: str,
):
    module, course = get_module_owned_with_course(db, teacher_id, module_id)
    if not module or not course:
        return {"error": "Không tìm thấy module hoặc bạn không có quyền cập nhật."}

    title = _clean_text(title)
    description = _clean_text(description)
    learning_objectives = _clean_text(learning_objectives)

    if not title:
        return {"error": "Tên chương không được để trống."}

    duplicate = (
        db.query(Module)
        .filter(
            Module.course_id == module.course_id,
            Module.module_number == module_number,
            Module.id != module_id,
            Module.deleted_at.is_(None)
        )
        .first()
    )
    if duplicate:
        return {"error": f"Module số {module_number} đã tồn tại trong khóa học này."}

    try:
        module.module_number = module_number
        module.title = title
        module.description = description
        module.learning_objectives = learning_objectives
        module.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(module)

        return {"success": True, "course_id": module.course_id}

    except SQLAlchemyError:
        db.rollback()
        return {"error": "Đã xảy ra lỗi khi cập nhật module."}


# =========================================================
# ❌ Xóa Module
# =========================================================
def delete_module(db: Session, teacher_id: str, module_id: str):
    module, course = get_module_owned_with_course(db, teacher_id, module_id)
    if not module or not course:
        return {"error": "Không tìm thấy module hoặc bạn không có quyền xóa."}

    if module.is_published == 1:
        return {"error": "Chương đã đăng, không thể xóa."}

    try:
        if hasattr(module, "deleted_at"):
            module.deleted_at = datetime.utcnow()
            module.updated_at = datetime.utcnow()
        else:
            db.delete(module)

        db.commit()
        return {"success": True, "course_id": module.course_id}

    except SQLAlchemyError:
        db.rollback()
        return {"error": "Đã xảy ra lỗi khi xóa module."}


# =========================================================
# 📢 Đăng / Gỡ đăng module
# =========================================================
def publish_module(db: Session, teacher_id: str, module_id: str, publish: bool):
    module, course = get_module_owned_with_course(db, teacher_id, module_id)
    if not module or not course:
        return {"error": "Không tìm thấy module hoặc không có quyền cập nhật trạng thái."}

    try:
        module.is_published = 1 if publish else 0
        module.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(module)
        return {"success": True, "module": module}

    except SQLAlchemyError:
        db.rollback()
        return {"error": "Không thể cập nhật trạng thái module."}