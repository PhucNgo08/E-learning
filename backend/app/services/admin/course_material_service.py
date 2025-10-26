from sqlalchemy.orm import Session
from app.models.course_material import CourseMaterial
from app.models.course import Course
from datetime import datetime
from pathlib import Path
import uuid, shutil, os

# ✅ Dùng cấu hình chuẩn trong app.config.paths
from app.config.paths import UPLOAD_MATERIALS

# ==========================================================
# 📋 1️⃣ Lấy danh sách tất cả tài liệu
# ==========================================================
def get_all(db: Session):
    """Trả về toàn bộ tài liệu khóa học."""
    return db.query(CourseMaterial).order_by(CourseMaterial.created_at.desc()).all()


# ==========================================================
# 🔍 2️⃣ Lấy thông tin 1 tài liệu theo ID
# ==========================================================
def get_by_id(db: Session, material_id: str):
    """Lấy thông tin tài liệu theo ID."""
    return db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()


# ==========================================================
# ➕ 3️⃣ Tạo mới tài liệu
# ==========================================================
async def create_material(db: Session, title, description, course_id, file, created_by: str):
    """Tạo tài liệu mới và lưu file upload vào thư mục uploads/materials."""
    if not created_by:
        raise ValueError("Thiếu thông tin người tạo (created_by).")

    # 🔒 Tạo tên file an toàn
    unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_MATERIALS / unique_name

    # Lưu file vật lý
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Ghi vào DB
    new_file = CourseMaterial(
        id=str(uuid.uuid4()),
        course_id=course_id,
        title=title.strip(),
        description=description.strip() if description else None,
        file_name=unique_name,
        file_url=f"/uploads/materials/{unique_name}",   # ✅ CHUẨN URL
        file_size=file_path.stat().st_size,
        file_format=file.filename.split(".")[-1].upper() if "." in file.filename else None,
        material_type="slide",
        created_by=created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file


# ==========================================================
# ✏️ 4️⃣ Cập nhật tài liệu
# ==========================================================
async def update_material(db: Session, material_id, title, description, file):
    """Cập nhật thông tin tài liệu và thay file mới nếu có."""
    material = get_by_id(db, material_id)
    if not material:
        return None

    material.title = title.strip()
    material.description = description.strip() if description else None

    if file:
        # Lưu file mới
        unique_name = f"{uuid.uuid4()}_{file.filename.replace(' ', '_')}"
        file_path = UPLOAD_MATERIALS / unique_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Xóa file cũ
        try:
            old_path = UPLOAD_MATERIALS / material.file_name
            if old_path.exists():
                old_path.unlink()
        except Exception as e:
            print(f"⚠️ Không thể xóa file cũ: {e}")

        # Cập nhật thông tin mới
        material.file_name = unique_name
        material.file_url = f"/uploads/materials/{unique_name}"
        material.file_size = file_path.stat().st_size
        material.file_format = file.filename.split(".")[-1].upper() if "." in file.filename else None

    material.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(material)
    return material


# ==========================================================
# 🗑️ 5️⃣ Xóa tài liệu
# ==========================================================
def delete_material(db: Session, material_id):
    """Xóa tài liệu khỏi cơ sở dữ liệu và xóa file vật lý."""
    material = get_by_id(db, material_id)
    if not material:
        return None

    # Xóa file vật lý nếu tồn tại
    try:
        file_path = UPLOAD_MATERIALS / material.file_name
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"⚠️ Không thể xóa file: {e}")

    db.delete(material)
    db.commit()
    return True


# ==========================================================
# 📘 6️⃣ Lấy danh sách tất cả khóa học
# ==========================================================
def get_all_courses(db: Session):
    """Lấy danh sách tất cả khóa học còn hoạt động để hiển thị trong form."""
    return (
        db.query(Course)
        .filter(Course.status != "archived")
        .order_by(Course.course_name.asc())
        .all()
    )


# ==========================================================
# 📊 7️⃣ Thống kê tổng quan
# ==========================================================
def get_statistics(db: Session):
    """Trả về thống kê cơ bản về tài liệu khóa học."""
    total = db.query(CourseMaterial).count()
    total_size = sum(m.file_size or 0 for m in db.query(CourseMaterial).all())
    public_count = (
        db.query(CourseMaterial)
        .filter(CourseMaterial.is_public == 1)
        .count()
        if hasattr(CourseMaterial, "is_public")
        else 0
    )
    return {
        "total_materials": total,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "public_count": public_count,
    }
