import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models.course import Course
from app.models.course_material import CourseMaterial

# ==============================
# 📁 Cấu hình thư mục lưu tài liệu
# ==============================
UPLOAD_DIR = Path("static/uploads/materials")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ==============================
# 🔒 Kiểm tra quyền sở hữu khóa học
# ==============================
def _course_owned(db: Session, teacher_id: str, course_id: str):
    """Kiểm tra xem giáo viên có quyền quản lý khóa học này không."""
    return (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )


# ==============================
# 📤 Upload tài liệu
# ==============================
async def upload_material(
    db: Session,
    teacher_id: str,
    course_id: str,
    material_type: str,
    title: str,
    description: str,
    file: UploadFile,
):
    """Upload file và lưu metadata vào DB."""
    course = _course_owned(db, teacher_id, course_id)
    if not course:
        return {"error": "Bạn không có quyền thêm tài liệu cho khóa học này."}

    try:
        # Lưu file vật lý
        file_id = str(uuid.uuid4())
        fname = f"{file_id}_{file.filename}"
        save_path = UPLOAD_DIR / fname

        with open(save_path, "wb") as buffer:
            buffer.write(await file.read())

        # Metadata
        file_size = save_path.stat().st_size
        file_format = Path(file.filename).suffix.replace(".", "").lower()

        # Ghi vào DB
        material = CourseMaterial(
            id=file_id,
            course_id=course_id,
            material_type=material_type,
            title=title,
            description=description,
            file_name=fname,
            file_url=f"/{save_path.as_posix()}",
            file_size=file_size,
            file_format=file_format,
            created_by=teacher_id,
            created_at=datetime.utcnow(),
        )
        db.add(material)
        db.commit()
        db.refresh(material)
        return {"success": True, "material": material}

    except Exception as e:
        db.rollback()
        return {"error": f"Lỗi khi upload tài liệu: {e}"}


# ==============================
# 📋 Lấy danh sách tài liệu
# ==============================
def list_materials(db: Session, teacher_id: str, course_id: str = None):
    """Lấy danh sách tài liệu theo giáo viên hoặc khóa học cụ thể."""
    query = db.query(CourseMaterial).join(Course, CourseMaterial.course_id == Course.id)
    query = query.filter(Course.teacher_id == teacher_id)
    if course_id:
        query = query.filter(CourseMaterial.course_id == course_id)

    materials = query.order_by(CourseMaterial.created_at.desc()).all()
    return materials


# ==============================
# 🗑️ Xóa tài liệu
# ==============================
def delete_material(db: Session, teacher_id: str, material_id: str):
    """Xóa tài liệu (cả DB + file)."""
    material = (
        db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(CourseMaterial.id == material_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not material:
        return {"error": "Không tìm thấy hoặc không có quyền xóa tài liệu này."}

    try:
        # Xóa file vật lý
        file_path = Path(material.file_url.strip("/"))
        if file_path.exists():
            os.remove(file_path)

        # Xóa trong DB
        db.delete(material)
        db.commit()
        return {"success": True, "message": f"Đã xóa tài liệu: {material.title}"}
    except Exception as e:
        db.rollback()
        return {"error": f"Lỗi khi xóa tài liệu: {e}"}
