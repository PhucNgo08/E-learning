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


# ======================================================
# ⚙️ Cấu hình thư mục upload
# ======================================================
UPLOAD_DIR = Path("static/uploads/materials")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ======================================================
# 📋 1️⃣ Lấy danh sách tài liệu của giáo viên
# ======================================================
def get_all(db: Session, teacher_id: str):
    """Trả về tất cả tài liệu của giáo viên."""
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
    """Lấy tài liệu thuộc khóa học của giáo viên."""
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
    """Tạo tài liệu mới cho giáo viên."""
    if not created_by:
        return {"error": "Thiếu thông tin người tạo (created_by)."}

    # Kiểm tra quyền sở hữu khóa học
    course = db.query(Course).filter(
        Course.id == course_id, Course.teacher_id == created_by
    ).first()

    if not course:
        return {"error": "❌ Bạn không có quyền thêm tài liệu cho khóa học này."}

    try:
        # 🔒 Tên file an toàn
        unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_DIR / unique_name

        # Lưu file vật lý
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ghi dữ liệu vào DB
        new_file = CourseMaterial(
            id=str(uuid.uuid4()),
            course_id=course_id,
            title=title.strip(),
            description=description.strip() if description else None,
            file_name=unique_name,
            file_url=f"/{file_path.as_posix()}",
            file_size=file_path.stat().st_size,
            file_format=file.filename.split(".")[-1].lower() if "." in file.filename else None,
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
    """Cập nhật tài liệu của giáo viên."""
    material = get_by_id(db, teacher_id, material_id)
    if not material:
        return {"error": "❌ Không tìm thấy hoặc không có quyền sửa tài liệu này."}

    material.title = title.strip()
    material.description = description.strip() if description else None

    if file:
        # Upload file mới
        unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_DIR / unique_name
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Xóa file cũ
        try:
            old_path = Path(material.file_url.strip("/"))
            if old_path.exists():
                old_path.unlink()
        except Exception as e:
            print(f"⚠️ Không thể xóa file cũ: {e}")

        # Cập nhật metadata
        material.file_name = unique_name
        material.file_url = f"/{file_path.as_posix()}"
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
    """Xóa tài liệu của giáo viên (DB + file vật lý)."""
    material = get_by_id(db, teacher_id, material_id)
    if not material:
        return {"error": "❌ Không tìm thấy hoặc không có quyền xóa tài liệu này."}

    try:
        file_path = Path(material.file_url.strip("/"))
        if file_path.exists():
            os.remove(file_path)
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
    """Lấy các khóa học mà giáo viên đang phụ trách."""
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
    """Thống kê tài liệu của giáo viên."""
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
