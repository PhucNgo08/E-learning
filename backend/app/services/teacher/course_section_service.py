"""
==========================================================
📘 app/services/teacher/course_section_service.py
Quản lý MODULE (phần học) cho giáo viên
==========================================================
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.module import Module


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _get_teacher_course(db: Session, course_id: str, teacher_id: str) -> Course | None:
    return (
        db.query(Course)
        .filter(
            Course.id == course_id,
            Course.teacher_id == teacher_id,
        )
        .first()
    )


def _get_owned_section(db: Session, section_id: str, teacher_id: str) -> Module | None:
    return (
        db.query(Module)
        .join(Course, Course.id == Module.course_id)
        .filter(
            Module.id == section_id,
            Course.teacher_id == teacher_id,
        )
        .first()
    )


def _next_module_number(db: Session, course_id: str) -> int:
    last_no = (
        db.query(func.max(Module.module_number))
        .filter(
            Module.course_id == course_id,
            Module.deleted_at.is_(None) if hasattr(Module, "deleted_at") else True,
        )
        .scalar()
    )
    return int(last_no or 0) + 1


# =====================================================
# 📋 1️⃣ Lấy danh sách module theo khóa học
# =====================================================
def get_all_sections(db: Session, course_id: str, teacher_id: str):
    """
    Lấy toàn bộ module thuộc một khóa học của giáo viên.
    """
    course = _get_teacher_course(db, course_id, teacher_id)
    if not course:
        return []

    query = db.query(Module).filter(Module.course_id == course_id)

    if hasattr(Module, "deleted_at"):
        query = query.filter(Module.deleted_at.is_(None))

    return query.order_by(Module.module_number.asc()).all()


# =====================================================
# 🔍 2️⃣ Lấy 1 module theo ID
# =====================================================
def get_section_by_id(db: Session, section_id: str, teacher_id: str):
    section = _get_owned_section(db, section_id, teacher_id)
    if not section:
        return None

    if hasattr(section, "deleted_at") and section.deleted_at is not None:
        return None

    return section


# =====================================================
# ➕ 3️⃣ Tạo module mới
# =====================================================
def create_section(
    db: Session,
    course_id: str,
    teacher_id: str,
    title: str,
    description: str | None = None,
    learning_objectives: str | None = None,
    estimated_duration: int | None = None,
    is_published: bool = False,
):
    """
    Tạo mới module trong khóa học của giáo viên.
    """
    title = _clean_text(title)
    description = _clean_text(description)
    learning_objectives = _clean_text(learning_objectives)

    if not title:
        raise ValueError("Tiêu đề module không được để trống.")

    course = _get_teacher_course(db, course_id, teacher_id)
    if not course:
        raise ValueError("Khóa học không tồn tại hoặc không thuộc quyền của giáo viên.")

    try:
        new_section = Module(
            id=str(uuid.uuid4()),
            course_id=course_id,
            module_number=_next_module_number(db, course_id),
            title=title,
            description=description,
            learning_objectives=learning_objectives,
            estimated_duration=estimated_duration,
            is_published=bool(is_published),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_section)
        db.commit()
        db.refresh(new_section)
        return new_section

    except SQLAlchemyError:
        db.rollback()
        raise


# =====================================================
# ✏️ 4️⃣ Cập nhật module
# =====================================================
def update_section(
    db: Session,
    section_id: str,
    teacher_id: str,
    title: str,
    description: str | None = None,
    learning_objectives: str | None = None,
    estimated_duration: int | None = None,
    is_published: bool = False,
):
    """
    Cập nhật thông tin module.
    """
    section = get_section_by_id(db, section_id, teacher_id)
    if not section:
        return None

    title = _clean_text(title)
    description = _clean_text(description)
    learning_objectives = _clean_text(learning_objectives)

    if not title:
        raise ValueError("Tiêu đề module không được để trống.")

    try:
        section.title = title
        section.description = description
        section.learning_objectives = learning_objectives
        section.estimated_duration = estimated_duration
        section.is_published = bool(is_published)
        section.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(section)
        return section

    except SQLAlchemyError:
        db.rollback()
        raise


# =====================================================
# 🔁 5️⃣ Sắp xếp lại thứ tự module
# =====================================================
def reorder_sections(
    db: Session,
    course_id: str,
    teacher_id: str,
    ordered_section_ids: list[str],
):
    """
    ordered_section_ids: danh sách id module theo thứ tự mới
    """
    course = _get_teacher_course(db, course_id, teacher_id)
    if not course:
        raise ValueError("Khóa học không tồn tại hoặc không thuộc quyền của giáo viên.")

    sections = get_all_sections(db, course_id, teacher_id)
    section_map = {s.id: s for s in sections}

    if set(ordered_section_ids) != set(section_map.keys()):
        raise ValueError("Danh sách module không hợp lệ.")

    try:
        for idx, section_id in enumerate(ordered_section_ids, start=1):
            section_map[section_id].module_number = idx
            section_map[section_id].updated_at = datetime.utcnow()

        db.commit()
        return True

    except SQLAlchemyError:
        db.rollback()
        raise


# =====================================================
# ❌ 6️⃣ Xóa module
# =====================================================
def delete_section(db: Session, section_id: str, teacher_id: str):
    """
    Ưu tiên soft delete nếu model có deleted_at.
    """
    section = get_section_by_id(db, section_id, teacher_id)
    if not section:
        return False

    try:
        if hasattr(section, "deleted_at"):
            section.deleted_at = datetime.utcnow()
            section.updated_at = datetime.utcnow()
        else:
            db.delete(section)

        db.commit()
        return True

    except SQLAlchemyError:
        db.rollback()
        raise