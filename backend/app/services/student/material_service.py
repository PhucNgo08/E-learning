"""
📘 Service: Materials (Tài liệu học tập)
Xử lý lấy danh sách và tải tài liệu của học viên
"""

from sqlalchemy.orm import Session
from app.models.course_material import CourseMaterial

def get_materials_by_course(db: Session, course_id: str):
    """Lấy danh sách tài liệu của khóa học"""
    return db.query(CourseMaterial).filter(CourseMaterial.course_id == course_id).all()
