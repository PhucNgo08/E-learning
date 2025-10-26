"""
==========================================================
📘 app/services/teacher/course_section_service.py
Quản lý MODULE (phần học) cho giáo viên
==========================================================
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.module import Module


# =====================================================
# 📋 1️⃣ Lấy danh sách module theo khóa học
# =====================================================
def get_all_sections(db: Session, course_id: str):
    """Lấy toàn bộ module thuộc một khóa học."""
    return (
        db.query(Module)
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number.asc())
        .all()
    )


# =====================================================
# ➕ 2️⃣ Tạo module mới
# =====================================================
def create_section(
    db: Session,
    course_id: str,
    title: str,
    description: str = None,
    learning_objectives: str = None,
    estimated_duration: int = None,
    is_published: bool = False,
):
    """Tạo mới module trong khóa học của giáo viên."""
    try:
        new_section = Module(
            id=str(uuid.uuid4()),
            course_id=course_id,
            title=title.strip(),
            description=description.strip() if description else None,
            learning_objectives=learning_objectives.strip() if learning_objectives else None,
            estimated_duration=estimated_duration,
            is_published=1 if is_published else 0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_section)
        db.commit()
        db.refresh(new_section)
        print(f"✅ [Teacher] Tạo module mới: {new_section.title}")
        return new_section
    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Teacher] Lỗi tạo module:", e)
        return {"error": str(e)}


# =====================================================
# ✏️ 3️⃣ Cập nhật module
# =====================================================
def update_section(
    db: Session,
    section_id: str,
    title: str,
    description: str = None,
    learning_objectives: str = None,
    estimated_duration: int = None,
    is_published: bool = False,
):
    """Cập nhật thông tin module."""
    section = db.query(Module).filter(Module.id == section_id).first()
    if not section:
        return {"error": "Không tìm thấy module để cập nhật."}

    try:
        section.title = title.strip()
        section.description = description.strip() if description else None
        section.learning_objectives = learning_objectives.strip() if learning_objectives else None
        section.estimated_duration = estimated_duration
        section.is_published = 1 if is_published else 0
        section.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(section)
        print(f"✏️ [Teacher] Cập nhật module: {section.title}")
        return section
    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Teacher] Lỗi cập nhật module:", e)
        return {"error": str(e)}


# =====================================================
# ❌ 4️⃣ Xóa module
# =====================================================
def delete_section(db: Session, section_id: str):
    """Xóa module khỏi khóa học."""
    section = db.query(Module).filter(Module.id == section_id).first()
    if not section:
        print("⚠️ [Teacher] Không tìm thấy module để xóa.")
        return False

    try:
        db.delete(section)
        db.commit()
        print(f"🗑️ [Teacher] Đã xóa module: {section.title}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Teacher] Lỗi xóa module:", e)
        return False
