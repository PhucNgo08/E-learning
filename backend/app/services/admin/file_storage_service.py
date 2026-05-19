"""
==========================================================
📦 SERVICE: File Storage Service
Xử lý upload, xóa, cache CDN và thống kê lưu trữ
==========================================================
"""
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.config.paths import UPLOAD_MATERIALS, UPLOADS_BASE, build_upload_url
from app.models.file_storage import FileStorage
from app.models.cdn_cache import CDNCache


ALLOWED_STORAGE_PROVIDERS = {"local", "s3", "cdn"}


def _safe_filename(filename: str) -> str:
    filename = (filename or "").strip()
    filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return filename


def _build_public_file_url(upload_root: str, stored_name: str) -> str:
    """
    Trả về URL public có thể mở trong trình duyệt.
    Tránh lỗi lưu file_url thành D:/... hoặc /mnt/... khiến giao diện không tải được.
    """
    root = Path(upload_root).resolve()
    base = UPLOADS_BASE.resolve()

    try:
        relative_dir = root.relative_to(base).as_posix()
        return f"/uploads/{relative_dir}/{stored_name}"
    except ValueError:
        # Nếu upload_dir custom nằm ngoài UPLOADS_BASE, vẫn fallback về materials.
        return build_upload_url("materials", stored_name)


def upload_file_service(
    file,
    db: Session,
    uploaded_by: str,
    storage_provider: str = "local",
    is_public: int = 1,
    upload_dir: str | None = None
):
    """
    Upload file vào thư mục chỉ định và lưu vào cơ sở dữ liệu.
    """
    if not file or not getattr(file, "filename", None):
        raise ValueError("Bạn chưa chọn file upload.")

    if storage_provider not in ALLOWED_STORAGE_PROVIDERS:
        raise ValueError("Storage provider không hợp lệ.")

    upload_root = str(UPLOAD_MATERIALS if not upload_dir else Path(upload_dir))
    os.makedirs(upload_root, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_name = _safe_filename(file.filename)
    if not safe_name:
        raise ValueError("Tên file không hợp lệ.")

    stored_name = f"{file_id}_{safe_name}"
    file_path = os.path.join(upload_root, stored_name)

    try:
        file.file.seek(0)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)
        file_url = _build_public_file_url(upload_root, stored_name)

        new_file = FileStorage(
            id=file_id,
            file_name=stored_name,
            original_name=file.filename,
            file_path=file_path,
            file_url=file_url,
            file_size=file_size,
            file_type=file.content_type,
            file_extension=os.path.splitext(file.filename)[1].lower(),
            storage_provider=storage_provider,
            is_public=int(is_public),
            uploaded_by=uploaded_by,
            created_at=datetime.utcnow(),
        )

        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return new_file

    except ValueError:
        db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise
    except SQLAlchemyError as e:
        db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise RuntimeError(f"Lỗi khi lưu file vào cơ sở dữ liệu: {str(e)}") from e
    except Exception as e:
        db.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise RuntimeError(f"Lỗi khi upload file: {str(e)}") from e


def delete_file_service(db: Session, file_id: str):
    """
    Xóa file khỏi DB và hệ thống lưu trữ.
    """
    file = db.query(FileStorage).filter(FileStorage.id == file_id).first()
    if not file:
        return None

    try:
        db.query(CDNCache).filter(CDNCache.file_id == file_id).delete(synchronize_session=False)

        if file.file_path and os.path.exists(file.file_path):
            try:
                os.remove(file.file_path)
            except Exception:
                pass

        db.delete(file)
        db.commit()
        return file

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa file: {str(e)}") from e


def refresh_cdn_cache_service(db: Session, file_id: str, cdn_provider: str = "cloudflare"):
    """
    Tạo hoặc cập nhật cache CDN cho file.
    """
    file = db.query(FileStorage).filter(FileStorage.id == file_id).first()
    if not file:
        return None

    try:
        existing_cache = db.query(CDNCache).filter(CDNCache.file_id == file_id).first()

        if existing_cache:
            existing_cache.cache_status = "refresh"
            existing_cache.cdn_provider = cdn_provider
            existing_cache.last_cache_hit = datetime.utcnow()
            existing_cache.cache_hit_count = (existing_cache.cache_hit_count or 0) + 1
        else:
            new_cache = CDNCache(
                id=str(uuid.uuid4()),
                file_id=file_id,
                cdn_url=f"https://cdn.example.com/{Path(file.file_url).name}",
                cdn_provider=cdn_provider,
                cache_status="hit",
                cache_key=file.id[:8],
                cache_control="public, max-age=3600",
                load_time_ms=120,
                cache_hit_count=1,
                last_cache_hit=datetime.utcnow(),
            )
            db.add(new_cache)

        db.commit()
        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật CDN cache: {str(e)}") from e


def get_storage_stats_service(db: Session):
    """
    Thống kê tổng dung lượng, số lượng file, và cache CDN.
    """
    total_files = db.query(FileStorage).count()
    total_size = db.query(func.sum(FileStorage.file_size)).scalar() or 0
    cdn_count = db.query(CDNCache).count()

    optimized_col = getattr(FileStorage, "is_optimized", None)
    if optimized_col is not None:
        optimized_files = db.query(FileStorage).filter(optimized_col == 1).count()
    else:
        optimized_files = 0

    return {
        "total_files": int(total_files),
        "total_size": round(total_size / (1024 * 1024), 2),
        "cdn_count": int(cdn_count),
        "optimized_files": int(optimized_files),
    }
