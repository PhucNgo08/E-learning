"""
==========================================================
📘 SERVICE: Student - Course Materials (Enrollment-based Access)
==========================================================
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.course_material import CourseMaterial
from app.services.common.course_access_service import has_course_access


def _active_material_filter():
    now = datetime.utcnow()
    return and_(
        or_(CourseMaterial.available_from.is_(None), CourseMaterial.available_from <= now),
        or_(CourseMaterial.available_to.is_(None), CourseMaterial.available_to >= now),
    )


def get_public_materials(db: Session):
    try:
        return (
            db.query(CourseMaterial)
            .filter(CourseMaterial.is_public == 1)
            .filter(_active_material_filter())
            .order_by(CourseMaterial.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_public_materials] Lỗi:", e)
        traceback.print_exc()
        return []


def get_materials_by_course(db: Session, course_id: str, student_id: str | None = None):
    try:
        query = (
            db.query(CourseMaterial)
            .filter(CourseMaterial.course_id == course_id)
            .filter(_active_material_filter())
        )

        if student_id and not has_course_access(db, student_id, course_id):
            query = query.filter(CourseMaterial.is_public == 1)

        return query.order_by(CourseMaterial.created_at.desc()).all()
    except Exception as e:
        print("❌ [get_materials_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


def get_material_detail(db: Session, material_id: str, student_id: str | None = None):
    try:
        material = (
            db.query(CourseMaterial)
            .filter(CourseMaterial.id == material_id)
            .filter(_active_material_filter())
            .first()
        )
        if not material:
            return None

        if int(getattr(material, "is_public", 0) or 0) == 1:
            return material

        if student_id and has_course_access(db, student_id, material.course_id):
            return material

        if student_id is None:
            return material

        return None
    except Exception as e:
        print("❌ [get_material_detail] Lỗi:", e)
        traceback.print_exc()
        return None


def increment_download_count(db: Session, material_id: str):
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


def get_favorite_materials(db: Session, student_id: str):
    try:
        return (
            db.query(CourseMaterial)
            .filter(CourseMaterial.is_public == 1)
            .filter(_active_material_filter())
            .order_by(CourseMaterial.download_count.desc(), CourseMaterial.created_at.desc())
            .limit(8)
            .all()
        )
    except Exception as e:
        print("❌ [get_favorite_materials] Lỗi:", e)
        traceback.print_exc()
        return []


def student_can_access_material(db: Session, student_id: str, course_id: str) -> bool:
    """
    Nguồn sự thật duy nhất: course_enrollments
    """
    try:
        return has_course_access(db, student_id, course_id)
    except Exception as e:
        print("❌ [student_can_access_material] Lỗi:", e)
        traceback.print_exc()
        return False


def resolve_material_file_path(material: CourseMaterial, uploads_base) -> Path | None:
    try:
        base = Path(uploads_base)
        candidates: list[Path] = []

        file_url = (getattr(material, "file_url", None) or "").strip()
        file_name = (getattr(material, "file_name", None) or "").strip()

        if file_url and not file_url.startswith(("http://", "https://")):
            cleaned = file_url.lstrip("/\\")
            if cleaned.startswith("uploads/"):
                cleaned = cleaned[len("uploads/"):]
            candidates.append(base / cleaned)
            candidates.append(Path(file_url))

        if file_name:
            candidates.append(base / file_name)
            candidates.append(Path(file_name))

        for path in candidates:
            if path.exists() and path.is_file():
                return path.resolve()

        return None

    except Exception as e:
        print("❌ [resolve_material_file_path] Lỗi:", e)
        traceback.print_exc()
        return None