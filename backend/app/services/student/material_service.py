"""
==========================================================
📘 SERVICE: Student - Materials
Xử lý truy vấn dữ liệu tài liệu học tập cho học viên
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.course_material import CourseMaterial


# ======================================================
# 🔹 Lấy danh sách tài liệu theo khóa học
# ======================================================
def get_materials_by_course(db: Session, course_id: str):
    """
    Lấy danh sách tất cả tài liệu trong một khóa học.
    """
    return (
        db.query(CourseMaterial)
        .filter(CourseMaterial.course_id == course_id)
        .order_by(CourseMaterial.created_at.desc())
        .all()
    )


# ======================================================
# 🔹 Lấy chi tiết tài liệu
# ======================================================
def get_material_detail(db: Session, material_id: str):
    """
    Lấy chi tiết một tài liệu học tập cụ thể theo ID.
    """
    return (
        db.query(CourseMaterial)
        .filter(CourseMaterial.id == material_id)
        .first()
    )


# ======================================================
# 🔹 Cập nhật lượt tải xuống
# ======================================================
def increment_download_count(db: Session, material_id: str):
    """
    Tăng số lượt tải xuống khi sinh viên tải file.
    """
    material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if material:
        material.download_count = (material.download_count or 0) + 1
        db.commit()
        db.refresh(material)
    return material
