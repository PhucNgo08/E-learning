from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import shutil
import mimetypes
import os

from app.models.course_material import CourseMaterial
from app.models.course_material_version import CourseMaterialVersion
from app.models.course import Course
from app.config.paths import UPLOAD_MATERIALS

# ==========================================================
# 🔐 VALIDATION
# ==========================================================

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "application/x-rar-compressed",
    "text/plain",
    "image/png",
    "image/jpeg",
    # Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    # Video
    "video/mp4"
}

FORBIDDEN_EXT = {"exe", "bat", "sh", "js", "msi", "apk"}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def validate_file(file):

    # kiểm tra ext nguy hiểm
    ext = file.filename.split(".")[-1].lower()
    if ext in FORBIDDEN_EXT:
        raise ValueError("❌ Tệp không an toàn, không được phép tải lên!")

    # kiểm tra dung lượng
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise ValueError("❌ File vượt quá giới hạn 100MB!")

    # kiểm tra MIME
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError(f"❌ Định dạng không hỗ trợ: {file.content_type}")

    return True


def safe_filename(filename: str):
    """ Chuyển filename sang dạng an toàn """
    filename = filename.replace(" ", "_")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")
    return filename


def detect_material_type(file) -> str:
    ext = file.filename.split(".")[-1].lower()

    if ext in {"ppt", "pptx"}:
        return "slide"
    if ext in {"pdf", "doc", "docx"}:
        return "textbook"
    if ext in {"zip", "rar"}:
        return "code"
    if ext in {"xlsx", "csv"}:
        return "spreadsheet"
    if ext in {"mp4"}:
        return "video"
    if ext in {"png", "jpg", "jpeg"}:
        return "image"
    return "reference"


# ==========================================================
# 📦 Helper: Save file + Create version
# ==========================================================
def save_file_and_create_version(db, material: CourseMaterial, file, version_str):

    UPLOAD_MATERIALS.mkdir(parents=True, exist_ok=True)

    validate_file(file)

    safe_name = safe_filename(file.filename)
    unique_name = f"{uuid.uuid4()}_{safe_name}"

    file_path = UPLOAD_MATERIALS / unique_name

    # lưu file vật lý
    file.file.seek(0)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    mime = mimetypes.guess_type(unique_name)[0] or file.content_type

    # tạo version trong DB
    new_version = CourseMaterialVersion(
        id=str(uuid.uuid4()),
        material_id=material.id,
        version=version_str,
        file_name=unique_name,
        file_url=f"/uploads/course_materials/{unique_name}",
        file_size=file_path.stat().st_size,
        file_format=safe_name.split(".")[-1].upper(),
        mime_type=mime,
        created_at=datetime.utcnow(),
    )

    db.add(new_version)

    # cập nhật bản chính
    material.file_name = unique_name
    material.file_url = new_version.file_url
    material.file_size = new_version.file_size
    material.file_format = new_version.file_format
    material.mime_type = mime
    material.version = version_str
    material.material_type = detect_material_type(file)
    material.updated_at = datetime.utcnow()


# ==========================================================
# 📌 1) Lấy tất cả tài liệu
# ==========================================================
def get_all(db: Session):
    return db.query(CourseMaterial).order_by(CourseMaterial.created_at.desc()).all()


# ==========================================================
# 📌 2) Lấy tài liệu theo ID
# ==========================================================
def get_by_id(db: Session, material_id: str):
    return db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()


# ==========================================================
# 📌 3) Tạo tài liệu – MULTIPLE UPLOAD
# ==========================================================
async def create_material(
    db: Session,
    title: str,
    description: str,
    course_id: str,
    files: list,
    created_by: str
):

    if not files or len(files) == 0:
        raise ValueError("Bạn phải chọn ít nhất 1 file!")

    # tạo tài liệu chính (placeholder để bypass NOT NULL)
    material = CourseMaterial(
        id=str(uuid.uuid4()),
        course_id=course_id,
        title=title.strip(),
        description=description.strip() if description else None,
        created_by=created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        version="1.0",

        # 🚑 FIX lỗi file_url cannot be null
        file_url="pending",
        file_name="pending",
        file_format="",
        mime_type="",
        file_size=0
    )

    db.add(material)
    db.flush()   # tạo ID để version link vào

    # tạo versions
    for idx, file in enumerate(files):
        version_str = f"1.{idx}"
        save_file_and_create_version(db, material, file, version_str)

    # cập nhật version cuối
    material.version = f"1.{len(files)-1}"

    db.commit()
    db.refresh(material)
    return material


# ==========================================================
# 📌 4) Update tài liệu (tạo version mới)
# ==========================================================
async def update_material(
    db: Session,
    material_id: str,
    title: str,
    description: str,
    file
):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu")

    material.title = title.strip()
    material.description = description.strip() if description else None

    # Không upload file mới → chỉ update metadata
    if not file:
        material.updated_at = datetime.utcnow()
        db.commit()
        return material

    # tăng phiên bản
    major, minor = map(int, material.version.split("."))
    new_minor = minor + 1
    new_version_str = f"{major}.{new_minor}"

    save_file_and_create_version(db, material, file, new_version_str)

    db.commit()
    db.refresh(material)
    return material


# ==========================================================
# 📌 5) Xóa tài liệu + toàn bộ phiên bản + file vật lý
# ==========================================================
def delete_material(db: Session, material_id: str):

    material = get_by_id(db, material_id)
    if not material:
        return False

    # xóa các phiên bản
    for v in material.versions:
        file_path = UPLOAD_MATERIALS / v.file_name
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass

    # xóa bản chính
    if material.file_name:
        file_path = UPLOAD_MATERIALS / material.file_name
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass

    db.delete(material)
    db.commit()
    return True


# ==========================================================
# 📌 6) Lấy danh sách khóa học
# ==========================================================
def get_all_courses(db: Session):
    return (
        db.query(Course)
        .filter(Course.status != "archived")
        .order_by(Course.course_name.asc())
        .all()
    )


# ==========================================================
# 📌 7) Tăng lượt tải
# ==========================================================
def increase_download_count(db: Session, material: CourseMaterial):
    material.download_count += 1
    db.commit()


# ==========================================================
# 📌 8) Download phiên bản mới nhất
# ==========================================================
def get_download_latest(db: Session, material_id: str):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu")

    file_path = UPLOAD_MATERIALS / material.file_name
    if not file_path.exists():
        raise ValueError("File không tồn tại trên server")

    return material, file_path


# ==========================================================
# 📌 9) Lấy danh sách phiên bản
# ==========================================================
def get_versions(db: Session, material_id: str):
    material = get_by_id(db, material_id)
    if not material:
        raise ValueError("Không tìm thấy tài liệu")

    return material.versions
