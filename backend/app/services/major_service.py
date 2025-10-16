import uuid
from sqlalchemy.orm import Session
from app.models.major import Major


# =========================================================
# 📋 Lấy tất cả ngành học
# =========================================================
def get_all_majors(db: Session):
    return db.query(Major).order_by(Major.major_name.asc()).all()


# =========================================================
# 🔍 Lấy ngành học theo ID
# =========================================================
def get_major_by_id(db: Session, major_id: str):
    return db.query(Major).filter(Major.id == major_id).first()


# =========================================================
# ➕ Tạo ngành học (kiểm tra trùng)
# =========================================================
def create_major(db: Session, major_code: str, major_name: str, faculty_name: str):
    existing = db.query(Major).filter(
        (Major.major_code == major_code) | (Major.major_name == major_name)
    ).first()
    if existing:
        raise RuntimeError("⚠️ Mã ngành hoặc tên ngành đã tồn tại trong hệ thống!")

    new_major = Major(
        id=str(uuid.uuid4()),
        major_code=major_code.strip(),
        major_name=major_name.strip(),
        faculty_name=faculty_name.strip() if faculty_name else None,
        is_active=True,
    )
    db.add(new_major)
    db.commit()
    db.refresh(new_major)
    return new_major


# =========================================================
# ✏️ Cập nhật ngành học
# =========================================================
def update_major(db: Session, major_id: str, major_code: str, major_name: str, faculty_name: str, is_active: bool):
    major = db.query(Major).filter(Major.id == major_id).first()
    if not major:
        return None

    major.major_code = major_code.strip()
    major.major_name = major_name.strip()
    major.faculty_name = faculty_name.strip() if faculty_name else None
    major.is_active = is_active
    db.commit()
    db.refresh(major)
    return major


# =========================================================
# ❌ Xóa ngành học
# =========================================================
def delete_major(db: Session, major_id: str):
    major = db.query(Major).filter(Major.id == major_id).first()
    if not major:
        return False

    db.delete(major)
    db.commit()
    return True
