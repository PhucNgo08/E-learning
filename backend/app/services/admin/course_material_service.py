from datetime import datetime
from pathlib import Path
from typing import List, Optional
import mimetypes
import os
import shutil
import uuid

from sqlalchemy.orm import Session

from app.config.paths import UPLOAD_MATERIALS, build_upload_url
from app.models.course import Course
from app.models.course_material import CourseMaterial
from app.models.course_material_version import CourseMaterialVersion


ALLOWED_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/plain",
    "application/zip",
    "application/x-rar-compressed",
    "application/vnd.rar",
    "image/png",
    "image/jpeg",
    "video/mp4",
}

FORBIDDEN_EXT = {"exe", "bat", "sh", "js", "msi", "apk", "com", "scr"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def validate_file(file) -> bool:
    if not file or not getattr(file, "filename", None):
        raise ValueError("Tệp tải lên không hợp lệ.")

    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext in FORBIDDEN_EXT:
        raise ValueError("Tệp không an toàn, không được phép tải lên.")

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise ValueError("File vượt quá giới hạn 100MB.")

    if file.content_type not in ALLOWED_TYPES:
        raise ValueError(f"Định dạng không hỗ trợ: {file.content_type}")

    return True


def safe_filename(filename: str) -> str:
    filename = filename.replace(" ", "_")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")
    return filename


def detect_material_type(file) -> str:
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext in {"ppt", "pptx"}:
        return "slide"
    if ext in {"pdf", "doc", "docx"}:
        return "textbook"
    if ext in {"zip", "rar"}:
        return "code"
    if ext in {"xlsx", "xls", "csv"}:
        return "spreadsheet"
    if ext in {"mp4"}:
        return "video"
    if ext in {"png", "jpg", "jpeg"}:
        return "image"
    return "reference"


def _next_version_string(current_version: Optional[str]) -> str:
    if not current_version:
        return "1.0"

    try:
        major, minor = current_version.split(".")
        return f"{int(major)}.{int(minor) + 1}"
    except Exception:
        return "1.0"


def save_file_and_create_version(db: Session, material: CourseMaterial, file, version_str: str) -> Path:
    UPLOAD_MATERIALS.mkdir(parents=True, exist_ok=True)

    validate_file(file)

    safe_name = safe_filename(file.filename)
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    file_path = UPLOAD_MATERIALS / unique_name

    file.file.seek(0)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    mime = mimetypes.guess_type(unique_name)[0] or file.content_type

    new_version = CourseMaterialVersion(
        id=str(uuid.uuid4()),
        material_id=material.id,
        version=version_str,
        file_name=unique_name,
        file_url=build_upload_url("materials", unique_name),
        file_size=file_path.stat().st_size,
        file_format=Path(safe_name).suffix.lower().lstrip(".").upper(),
        mime_type=mime,
        created_at=datetime.utcnow(),
    )

    db.add(new_version)

    material.file_name = unique_name
    material.file_url = new_version.file_url
    material.file_size = new_version.file_size
    material.file_format = new_version.file_format
    material.mime_type = mime
    material.version = version_str
    material.material_type = detect_material_type(file)
    material.updated_at = datetime.utcnow()

    return file_path


def get_all(db: Session):
    return db.query(CourseMaterial).order_by(CourseMaterial.created_at.desc()).all()


def get_by_id(db: Session, material_id: str):
    return db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()


def get_all_courses(db: Session):
    return (
        db.query(Course)
        .filter(Course.status != "archived")
        .order_by(Course.course_name.asc())
        .all()
    )


async def create_material(
    db: Session,
    title: str,
    description: Optional[str],
    course_id: str,
    files: List,
    created_by: str,
):
    if not title or not title.strip():
        raise ValueError("Tiêu đề tài liệu không được để trống.")

    if not files or len(files) == 0:
        raise ValueError("Bạn phải chọn ít nhất 1 file.")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Khóa học không tồn tại.")

    material = CourseMaterial(
        id=str(uuid.uuid4()),
        course_id=course_id,
        title=title.strip(),
        description=description.strip() if description else None,
        created_by=created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        version="1.0",
        file_url="pending",
        file_name="pending",
        file_format="",
        mime_type="",
        file_size=0,
        download_count=0,
    )

    saved_paths: List[Path] = []

    try:
        db.add(material)
        db.flush()

        for idx, file in enumerate(files):
            version_str = f"1.{idx}"
            saved_path = save_file_and_create_version(db, material, file, version_str)
            saved_paths.append(saved_path)

        material.version = f"1.{len(files) - 1}"
        db.commit()
        db.refresh(material)
        return material

    except Exception:
        db.rollback()
        for path in saved_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        raise


async def update_material(
    db: Session,
    material_id: str,
    title: str,
    description: Optional[str],
    file,
):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu.")

    if not title or not title.strip():
        raise ValueError("Tiêu đề tài liệu không được để trống.")

    material.title = title.strip()
    material.description = description.strip() if description else None

    if not file or not getattr(file, "filename", None):
        material.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(material)
        return material

    saved_path: Optional[Path] = None

    try:
        new_version_str = _next_version_string(material.version)
        saved_path = save_file_and_create_version(db, material, file, new_version_str)
        db.commit()
        db.refresh(material)
        return material

    except Exception:
        db.rollback()
        if saved_path:
            try:
                if saved_path.exists():
                    saved_path.unlink()
            except Exception:
                pass
        raise


def delete_material(db: Session, material_id: str):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu.")

    try:
        file_names = set()

        for v in material.versions:
            if v.file_name:
                file_names.add(v.file_name)
            db.delete(v)

        if material.file_name:
            file_names.add(material.file_name)

        for file_name in file_names:
            file_path = UPLOAD_MATERIALS / file_name
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

        db.delete(material)
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa tài liệu: {str(e)}") from e


def increase_download_count(db: Session, material: CourseMaterial):
    material.download_count = (material.download_count or 0) + 1
    db.commit()
    db.refresh(material)
    return material.download_count


def get_download_latest(db: Session, material_id: str):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu.")

    file_path = UPLOAD_MATERIALS / material.file_name
    if not file_path.exists():
        raise ValueError("File không tồn tại trên server.")

    return material, file_path


def get_versions(db: Session, material_id: str):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu.")

    return sorted(
        list(material.versions),
        key=lambda v: v.created_at or datetime.min,
        reverse=True,
    )
