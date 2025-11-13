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
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.file_storage import FileStorage
from app.models.cdn_cache import CDNCache


# ======================================================
# 📤 Upload file mới
# ======================================================
def upload_file_service(
    file,
    db: Session,
    uploaded_by: str,
    storage_provider: str = "local",
    is_public: int = 1,
    upload_dir: str = "app/uploads/materials"
):
    """
    Upload file vào thư mục chỉ định và lưu vào cơ sở dữ liệu.
    """
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_name = file.filename.replace(" ", "_")
    file_path = os.path.join(upload_dir, f"{file_id}_{safe_name}")

    # 🧾 Ghi file vật lý
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)
    file_url = f"/{file_path.replace(os.sep, '/')}"

    new_file = FileStorage(
        id=file_id,
        file_name=safe_name,
        original_name=file.filename,
        file_path=file_path,
        file_url=file_url,
        file_size=file_size,
        file_type=file.content_type,
        file_extension=os.path.splitext(file.filename)[1],
        storage_provider=storage_provider,
        is_public=is_public,
        uploaded_by=uploaded_by,
        created_at=datetime.utcnow(),
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)
    return new_file


# ======================================================
# 🗑️ Xóa file
# ======================================================
def delete_file_service(db: Session, file_id: str):
    """
    Xóa file khỏi DB và hệ thống lưu trữ (nếu tồn tại file vật lý)
    """
    file = db.query(FileStorage).filter(FileStorage.id == file_id).first()
    if not file:
        return None

    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        print(f"⚠️ Không thể xóa file vật lý: {e}")

    db.delete(file)
    db.commit()
    return file


# ======================================================
# 🔁 Làm mới CDN Cache
# ======================================================
def refresh_cdn_cache_service(db: Session, file_id: str, cdn_provider: str = "cloudflare"):
    """
    Tạo hoặc cập nhật cache CDN cho file
    """
    file = db.query(FileStorage).filter(FileStorage.id == file_id).first()
    if not file:
        return None

    existing_cache = db.query(CDNCache).filter(CDNCache.file_id == file_id).first()

    if existing_cache:
        # Nếu đã có cache → cập nhật lại
        existing_cache.cache_status = "refresh"
        existing_cache.last_cache_hit = datetime.utcnow()
        existing_cache.cache_hit_count += 1
    else:
        # Nếu chưa có cache → tạo mới
        new_cache = CDNCache(
            id=str(uuid.uuid4()),
            file_id=file_id,
            cdn_url=f"https://cdn.example.com/{os.path.basename(file.file_url)}",
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


# ======================================================
# 📊 Thống kê lưu trữ
# ======================================================
def get_storage_stats_service(db: Session):
    """
    Thống kê tổng dung lượng, số lượng file, và cache CDN
    """
    total_files = db.query(FileStorage).count()
    total_size = db.query(func.sum(FileStorage.file_size)).scalar() or 0
    cdn_count = db.query(CDNCache).count()
    optimized_files = db.query(FileStorage).filter(
        getattr(FileStorage, "is_optimized", 0) == 1
    ).count()

    return {
        "total_files": total_files,
        "total_size": round(total_size / (1024 * 1024), 2),
        "cdn_count": cdn_count,
        "optimized_files": optimized_files,
    }
