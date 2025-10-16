import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.module import Module
from app.models.course import Course


# =========================================================
# 🔒 Kiểm tra quyền sở hữu khóa học
# =========================================================
def _course_owned(db: Session, teacher_id: str, course_id: str):
    """Kiểm tra giáo viên có sở hữu khóa học này không."""
    return (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )


# =========================================================
# 📋 Danh sách Module theo khóa học
# =========================================================
def list_modules_by_course(db: Session, course_id: str):
    """Trả về danh sách module của một khóa học."""
    return (
        db.query(Module)
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number.asc())
        .all()
    )


# =========================================================
# 📚 Danh sách tất cả module của giáo viên
# =========================================================
def list_all_modules_by_teacher(db: Session, teacher_id: str):
    """Trả về toàn bộ module mà giáo viên sở hữu."""
    return (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
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
    """Tạo module mới trong khóa học của giáo viên."""
    try:
        # Kiểm tra quyền
        course = _course_owned(db, teacher_id, course_id)
        if not course:
            return {"error": "Bạn không có quyền tạo module cho khóa học này."}

        # Kiểm tra trùng module_number
        existed = (
            db.query(Module)
            .filter(Module.course_id == course_id, Module.module_number == module_number)
            .first()
        )
        if existed:
            return {"error": "Thứ tự module đã tồn tại trong khóa học này."}

        new_module = Module(
            id=str(uuid.uuid4()),
            course_id=course_id,
            module_number=module_number,
            title=title.strip(),
            description=description.strip() if description else None,
            learning_objectives=learning_objectives.strip() if learning_objectives else None,
            is_published=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_module)
        db.commit()
        db.refresh(new_module)

        print(f"✅ [Tạo module] {new_module.title} (#{new_module.module_number}) thuộc khóa học {course.course_name}")
        return new_module

    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Lỗi tạo module]", str(e))
        return {"error": "Đã xảy ra lỗi khi tạo module."}


# =========================================================
# 🔍 Lấy thông tin Module + kiểm tra quyền
# =========================================================
def get_module_owned_with_course(db: Session, teacher_id: str, module_id: str):
    """Trả về (module, course) nếu giáo viên có quyền truy cập."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        print("⚠️ [Module] Không tồn tại.")
        return None, None

    course = _course_owned(db, teacher_id, module.course_id)
    if not course:
        print("⛔ [Từ chối] Giáo viên không sở hữu khóa học chứa module này.")
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
    """Cập nhật thông tin module."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        print("⚠️ [Cập nhật] Không tìm thấy module.")
        return None

    course = _course_owned(db, teacher_id, module.course_id)
    if not course:
        print("⛔ [Từ chối] Không có quyền chỉnh sửa module này.")
        return None

    # Kiểm tra trùng thứ tự module
    duplicate = (
        db.query(Module)
        .filter(
            Module.course_id == module.course_id,
            Module.module_number == module_number,
            Module.id != module_id,
        )
        .first()
    )
    if duplicate:
        print(f"⚠️ [Cập nhật] Module số {module_number} đã tồn tại.")
        return None

    # Cập nhật thông tin
    module.module_number = module_number
    module.title = title.strip()
    module.description = description.strip() if description else None
    module.learning_objectives = learning_objectives.strip() if learning_objectives else None
    module.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(module)

    print(f"✏️ [Cập nhật] Module '{module.title}' đã được chỉnh sửa.")
    return module.course_id


# =========================================================
# ❌ Xóa Module
# =========================================================
def delete_module(db: Session, teacher_id: str, module_id: str):
    """Xóa hoặc đánh dấu xóa module."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        print("⚠️ [Xóa] Không tìm thấy module.")
        return None

    course = _course_owned(db, teacher_id, module.course_id)
    if not course:
        print("⛔ [Từ chối] Không có quyền xóa module này.")
        return None

    if hasattr(module, "deleted_at"):
        module.deleted_at = datetime.utcnow()
        print(f"🕒 [Xóa mềm] Module '{module.title}' đã được đánh dấu xóa.")
    else:
        db.delete(module)
        print(f"🗑️ [Xóa cứng] Module '{module.title}' đã bị xóa hoàn toàn.")

    db.commit()
    return module.course_id


# =========================================================
# 📢 Đăng / Gỡ đăng module
# =========================================================
def publish_module(db: Session, teacher_id: str, module_id: str, publish: bool):
    """Cập nhật trạng thái xuất bản module."""
    module, course = get_module_owned_with_course(db, teacher_id, module_id)
    if not module:
        print("⚠️ [Xuất bản] Không tìm thấy module hoặc không có quyền.")
        return None

    module.is_published = 1 if publish else 0
    module.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(module)

    state = "✅ [Xuất bản]" if publish else "🚫 [Gỡ đăng]"
    print(f"{state} Module '{module.title}' thuộc khóa học '{course.course_name}'.")
    return module
