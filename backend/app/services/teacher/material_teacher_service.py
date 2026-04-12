"""
==========================================================
👩‍🏫 Service: Teacher - Materials
Xử lý tài liệu khóa học cho giáo viên (upload, sửa, xóa)
==========================================================
"""
from datetime import datetime
import shutil
import uuid

from sqlalchemy.orm import Session
from app.models.course_material import CourseMaterial
from app.models.course import Course

from app.config.paths import UPLOAD_MATERIALS, build_upload_url


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _detect_material_type(file_format: str | None) -> str:
    ext = (file_format or "").lower()
    if ext in {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx"}:
        return "document"
    if ext in {"mp4", "avi", "mov", "mkv"}:
        return "video"
    if ext in {"zip", "rar", "7z"}:
        return "archive"
    if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
        return "image"
    return "file"


# ======================================================
# 📋 1️⃣ Lấy danh sách tài liệu của giáo viên
# ======================================================
def get_all(db: Session, teacher_id: str):
    return (
        db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(CourseMaterial.created_at.desc())
        .all()
    )


# ======================================================
# 🔍 2️⃣ Lấy thông tin 1 tài liệu theo ID
# ======================================================
def get_by_id(db: Session, teacher_id: str, material_id: str):
    return (
        db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(
            CourseMaterial.id == material_id,
            Course.teacher_id == teacher_id
        )
        .first()
    )


# ======================================================
# ➕ 3️⃣ Tạo tài liệu mới
# ======================================================
async def create_material(db: Session, title, description, course_id, file, created_by: str):
    title = _clean_text(title)
    description = _clean_text(description)

    if not created_by:
        return {"error": "Thiếu thông tin người tạo (created_by)."}

    if not title:
        return {"error": "Tiêu đề tài liệu không được để trống."}

    if not file or not getattr(file, "filename", None):
        return {"error": "Vui lòng chọn file để tải lên."}

    course = db.query(Course).filter(
        Course.id == course_id,
        Course.teacher_id == created_by
    ).first()

    if not course:
        return {"error": "Bạn không có quyền thêm tài liệu cho khóa học này."}

    try:
        UPLOAD_MATERIALS.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_MATERIALS / unique_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""

        new_file = CourseMaterial(
            id=str(uuid.uuid4()),
            course_id=course_id,
            title=title,
            description=description,
            file_name=unique_name,
            file_url=build_upload_url("materials", unique_name),
            file_size=file_path.stat().st_size,
            file_format=ext,
            material_type=_detect_material_type(ext),
            created_by=created_by,
            is_public=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return {"success": True, "material": new_file}

    except Exception as e:
        db.rollback()
        if "file_path" in locals() and file_path.exists():
            file_path.unlink()
        return {"error": f"Lỗi khi upload tài liệu: {e}"}


# ======================================================
# ✏️ 4️⃣ Cập nhật tài liệu
# ======================================================
async def update_material(db: Session, teacher_id: str, material_id, title, description, file=None):
    material = get_by_id(db, teacher_id, material_id)
    if not material:
        return {"error": "Không tìm thấy hoặc không có quyền sửa tài liệu này."}

    title = _clean_text(title)
    description = _clean_text(description)

    if not title:
        return {"error": "Tiêu đề tài liệu không được để trống."}

    old_file_name = material.file_name
    new_file_path = None

    try:
        material.title = title
        material.description = description

        if file and getattr(file, "filename", None):
            unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
            new_file_path = UPLOAD_MATERIALS / unique_name

            with open(new_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""

            material.file_name = unique_name
            material.file_url = build_upload_url("materials", unique_name)
            material.file_size = new_file_path.stat().st_size
            material.file_format = ext
            material.material_type = _detect_material_type(ext)

        material.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(material)

        if new_file_path and old_file_name:
            old_path = UPLOAD_MATERIALS / old_file_name
            if old_path.exists():
                old_path.unlink()

        return {"success": True, "material": material}

    except Exception as e:
        db.rollback()
        if new_file_path and new_file_path.exists():
            new_file_path.unlink()
        return {"error": f"Lỗi khi cập nhật tài liệu: {e}"}


# ======================================================
# 🗑️ 5️⃣ Xóa tài liệu
# ======================================================
def delete_material(db: Session, teacher_id: str, material_id: str):
    material = get_by_id(db, teacher_id, material_id)
    if not material:
        return {"error": "Không tìm thấy hoặc không có quyền xóa tài liệu này."}

    try:
        file_path = UPLOAD_MATERIALS / material.file_name
        if file_path.exists():
            file_path.unlink()

        db.delete(material)
        db.commit()
        return {"success": True, "message": f"Đã xóa tài liệu: {material.title}"}
    except Exception as e:
        db.rollback()
        return {"error": f"Lỗi khi xóa tài liệu: {e}"}


# ======================================================
# 📘 6️⃣ Lấy danh sách khóa học của giáo viên
# ======================================================
def get_courses_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id, Course.status != "archived")
        .order_by(Course.course_name.asc())
        .all()
    )


# ======================================================
# 📊 7️⃣ Thống kê nhanh
# ======================================================
def get_statistics(db: Session, teacher_id: str):
    materials = (
        db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .all()
    )

    total = len(materials)
    total_size = sum((m.file_size or 0) for m in materials)

    public_count = (
        sum(1 for m in materials if getattr(m, "is_public", False))
        if hasattr(CourseMaterial, "is_public")
        else 0
    )

    return {
        "total_materials": total,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "public_count": public_count,
    }
