"""
==========================================================
📘 SERVICE: Student - Materials
Xử lý truy vấn dữ liệu tài liệu học tập cho học viên
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.course_material import CourseMaterial
from datetime import datetime
import traceback


# ======================================================
# 🔹 Lấy danh sách tài liệu theo khóa học
# ======================================================
def get_materials_by_course(db: Session, course_id: str):
    """Lấy danh sách tất cả tài liệu trong một khóa học."""
    try:
        return (
            db.query(CourseMaterial)
            .filter(CourseMaterial.course_id == course_id)
            .order_by(CourseMaterial.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_materials_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 🔹 Lấy chi tiết tài liệu
# ======================================================
def get_material_detail(db: Session, material_id: str):
    """Lấy chi tiết một tài liệu học tập cụ thể theo ID."""
    try:
        return db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    except Exception as e:
        print("❌ [get_material_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Cập nhật lượt tải xuống
# ======================================================
def increment_download_count(db: Session, material_id: str):
    """Tăng số lượt tải xuống khi sinh viên tải file."""
    try:
        material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
        if material:
            material.download_count = (material.download_count or 0) + 1
            material.last_download_at = datetime.utcnow()
            db.commit()
            db.refresh(material)
        return material
    except Exception as e:
        db.rollback()
        print("❌ [increment_download_count] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Lấy danh sách tài liệu yêu thích (tùy chọn)
# ======================================================
def get_favorite_materials(db: Session, student_id: str):
    """
    Trả danh sách tài liệu học viên đã đánh dấu yêu thích.
    ⚠️ Nếu chưa có bảng favorites → trả về danh sách trống (mock tạm).
    """
    try:
        materials = (
            db.query(CourseMaterial)
            .filter(CourseMaterial.is_public == True)
            .order_by(CourseMaterial.created_at.desc())
            .limit(5)
            .all()
        )
        return materials
    except Exception as e:
        print("❌ [get_favorite_materials] Lỗi:", e)
        traceback.print_exc()
        return []
