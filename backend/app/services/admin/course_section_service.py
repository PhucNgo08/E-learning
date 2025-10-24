"""
==========================================================
📘 app/services/admin/course_section_service.py
Quản lý HỌC PHẦN (Course Section) – Dành cho ADMIN
==========================================================
"""

import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.course_section import CourseSection


# =====================================================
# ➕ 1️⃣ Tạo học phần mới
# =====================================================
def create_section(
    db: Session,
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int,
    location: str,
    schedule_info: str,
):
    """Tạo học phần mới"""
    try:
        new_section = CourseSection(
            id=str(uuid.uuid4()),
            section_code=section_code.strip(),
            section_name=section_name.strip(),
            course_id=course_id,
            max_students=max_students,
            location=location.strip() if location else None,
            schedule_info=schedule_info.strip() if schedule_info else None,
        )
        db.add(new_section)
        db.commit()
        db.refresh(new_section)
        print(f"✅ [ADMIN] Tạo học phần mới: {new_section.section_name}")
        return new_section
    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [ADMIN] Lỗi khi tạo học phần:", e)
        raise RuntimeError(f"Lỗi khi tạo học phần: {str(e)}")


# =====================================================
# 📋 2️⃣ Lấy danh sách học phần
# =====================================================
def get_all_sections(db: Session):
    """Lấy toàn bộ học phần"""
    try:
        sections = (
            db.query(CourseSection)
            .order_by(CourseSection.section_code.asc())
            .all()
        )
        print(f"📚 [ADMIN] Tổng số học phần: {len(sections)}")
        return sections
    except SQLAlchemyError as e:
        print("❌ [ADMIN] Lỗi khi truy vấn học phần:", e)
        raise RuntimeError(f"Lỗi khi truy vấn học phần: {str(e)}")


# =====================================================
# ✏️ 3️⃣ Cập nhật học phần
# =====================================================
def update_section(
    db: Session,
    section_id: str,
    section_code: str,
    section_name: str,
    course_id: str,
    max_students: int,
    location: str,
    schedule_info: str,
):
    """Cập nhật thông tin học phần"""
    section = db.query(CourseSection).filter(CourseSection.id == section_id).first()
    if not section:
        raise ValueError("Không tìm thấy học phần cần cập nhật.")

    try:
        section.section_code = section_code.strip()
        section.section_name = section_name.strip()
        section.course_id = course_id
        section.max_students = max_students
        section.location = location.strip() if location else None
        section.schedule_info = schedule_info.strip() if schedule_info else None

        db.commit()
        db.refresh(section)
        print(f"✏️ [ADMIN] Đã cập nhật học phần: {section.section_name}")
        return section
    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [ADMIN] Lỗi khi cập nhật học phần:", e)
        raise RuntimeError(f"Lỗi khi cập nhật học phần: {str(e)}")


# =====================================================
# ❌ 4️⃣ Xóa học phần
# =====================================================
def delete_section(db: Session, section_id: str):
    """Xóa học phần khỏi hệ thống"""
    section = db.query(CourseSection).filter(CourseSection.id == section_id).first()
    if not section:
        raise ValueError("Không tìm thấy học phần để xóa.")

    try:
        db.delete(section)
        db.commit()
        print(f"🗑️ [ADMIN] Đã xóa học phần: {section.section_name}")
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [ADMIN] Lỗi khi xóa học phần:", e)
        raise RuntimeError(f"Lỗi khi xóa học phần: {str(e)}")
