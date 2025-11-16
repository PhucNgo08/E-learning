"""
==========================================================
📘 SERVICE: Student - Course Materials
Xử lý dữ liệu tài liệu học tập cho học viên
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.course_material import CourseMaterial
from datetime import datetime
import traceback


# ======================================================
# 🔹 Helper: lọc theo thời gian mở/đóng
# ======================================================
def _active_material_filter():
    """Filter hiển thị tài liệu trong thời gian cho phép."""
    now = datetime.utcnow()
    return and_(
        or_(CourseMaterial.available_from == None,
            CourseMaterial.available_from <= now),
        or_(CourseMaterial.available_to == None,
            CourseMaterial.available_to >= now)
    )


# ======================================================
# 🔹 Lấy danh sách tài liệu theo khóa học
# ======================================================
def get_materials_by_course(db: Session, course_id: str):
    """Lấy danh sách tài liệu trong một khóa học."""
    try:
        return (
            db.query(CourseMaterial)
            .filter(CourseMaterial.course_id == course_id)
            .filter(_active_material_filter())
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
    """Lấy chi tiết một tài liệu (nếu trong thời gian cho phép)."""

    try:
        return (
            db.query(CourseMaterial)
            .filter(CourseMaterial.id == material_id)
            .filter(_active_material_filter())
            .first()
        )

    except Exception as e:
        print("❌ [get_material_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Tăng lượt tải xuống
# ======================================================
def increment_download_count(db: Session, material_id: str):
    """Tăng số lượt tải xuống và cập nhật thời gian tải cuối."""

    try:
        material = (
            db.query(CourseMaterial)
            .filter(CourseMaterial.id == material_id)
            .first()
        )

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
# 🔹 Lấy danh sách tài liệu nổi bật / yêu thích (mock)
# ======================================================
def get_favorite_materials(db: Session, student_id: str):
    """
    Lấy tài liệu gợi ý / yêu thích.
    ⚠️ Nếu bạn chưa có bảng favorites → mock bằng tài liệu public.
    """

    try:

        return (
            db.query(CourseMaterial)
            .filter(CourseMaterial.is_public == 1)
            .filter(_active_material_filter())
            .order_by(CourseMaterial.created_at.desc())
            .limit(5)
            .all()
        )

    except Exception as e:
        print("❌ [get_favorite_materials] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 🔹 (OPTIONAL) Kiểm tra SV có quyền xem tài liệu
# ======================================================
def student_can_access_material(db: Session, student_id: str, course_id: str) -> bool:
    """
    Kiểm tra học viên có được xem tài liệu hay không.
    - Có thể nâng cấp:
        • kiểm tra đã mua khóa học
        • kiểm tra enrollment
        • kiểm tra khóa học miễn phí
    """

    # TODO: Tùy bạn muốn bật quyền kiểm tra gì
    # Mặc định **cho phép tất cả SV** xem tài liệu của khóa đã tham gia
    return True
