"""
==========================================================
👩‍🏫 Service: Teacher - Materials
Xử lý tài liệu khóa học cho giáo viên (upload, sửa, xóa)
==========================================================
"""
from sqlalchemy.orm import Session
from app.models.course_material import CourseMaterial
from app.models.course import Course
from datetime import datetime
from pathlib import Path
import uuid, shutil, os

# ✅ Dùng đường dẫn chuẩn
from app.config.paths import UPLOAD_MATERIALS


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
    if not created_by:
        return {"error": "Thiếu thông tin người tạo (created_by)."}

    # Kiểm tra quyền sở hữu khóa học
    course = db.query(Course).filter(
        Course.id == course_id, Course.teacher_id == created_by
    ).first()

    if not course:
        return {"error": "❌ Bạn không có quyền thêm tài liệu cho khóa học này."}

    try:
        unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_MATERIALS / unique_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        new_file = CourseMaterial(
            id=str(uuid.uuid4()),
            course_id=course_id,
            title=title.strip(),
            description=description.strip() if description else None,
            file_name=unique_name,
            file_url=f"/uploads/materials/{unique_name}",  # ✅ đúng
            file_size=file_path.stat().st_size,
            file_format=file.filename.split(".")[-1].lower(),
            material_type="slide",
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
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        return {"error": f"Lỗi khi upload tài liệu: {e}"}


# ======================================================
# ✏️ 4️⃣ Cập nhật tài liệu
# ======================================================
async def update_material(db: Session, teacher_id: str, material_id, title, description, file=None):
    material = get_by_id(db, teacher_id, material_id)
    if not material:
        return {"error": "❌ Không tìm thấy hoặc không có quyền sửa tài liệu này."}

    material.title = title.strip()
    material.description = description.strip() if description else None

    if file:
        unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_MATERIALS / unique_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            old_path = UPLOAD_MATERIALS / material.file_name
            if old_path.exists():
                old_path.unlink()
        except Exception as e:
            print(f"⚠️ Không thể xóa file cũ: {e}")

        material.file_name = unique_name
        material.file_url = f"/uploads/materials/{unique_name}"
        material.file_size = file_path.stat().st_size
        material.file_format = file.filename.split(".")[-1].lower()

    material.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(material)
    return {"success": True, "material": material}


# ======================================================
# 🗑️ 5️⃣ Xóa tài liệu
# ======================================================
def delete_material(db: Session, teacher_id: str, material_id: str):
    material = get_by_id(db, teacher_id, material_id)
    if not material:
        return {"error": "❌ Không tìm thấy hoặc không có quyền xóa tài liệu này."}

    try:
        file_path = UPLOAD_MATERIALS / material.file_name
        if file_path.exists():
            file_path.unlink()
        db.delete(material)
        db.commit()
        return {"success": True, "message": f"✅ Đã xóa tài liệu: {material.title}"}
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
    total = (
        db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .count()
    )

    total_size = sum(
        m.file_size or 0
        for m in db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .all()
    )

    public_count = (
        db.query(CourseMaterial)
        .join(Course, CourseMaterial.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id, CourseMaterial.is_public == 1)
        .count()
        if hasattr(CourseMaterial, "is_public")
        else 0
    )

    return {
        "total_materials": total,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "public_count": public_count,
    }
