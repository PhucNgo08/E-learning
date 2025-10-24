from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.backup_history import BackupHistory
from datetime import datetime
import uuid
import os
from pathlib import Path

# 🧭 Thư mục lưu file backup vật lý (tùy chỉnh theo dự án)
BACKUP_DIR = Path("D:/KhoaHoctructuyen/KHoaHocOnline/backend/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# 📋 Lấy danh sách tất cả backup
def get_all_backups(db: Session):
    """
    Lấy toàn bộ danh sách bản sao lưu, sắp xếp mới nhất lên đầu.
    """
    try:
        return (
            db.query(BackupHistory)
            .order_by(BackupHistory.created_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách backup: {str(e)}")


# 💾 Tạo bản sao lưu mới (giả lập tạo file .sql)
def create_backup(database_name: str, backup_type: str, db: Session):
    """
    Tạo một bản sao lưu mới trong hệ thống và ghi vào DB.
    """
    try:
        now = datetime.now()
        file_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}.sql"
        file_path = BACKUP_DIR / file_name

        # 🧱 Tạo file rỗng giả lập backup
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"-- Backup giả lập cho database: {database_name}\n")
            f.write(f"-- Thời gian: {now}\n")

        # 🧩 Lưu vào DB
        new_backup = BackupHistory(
            id=str(uuid.uuid4()),
            backup_type=backup_type or "full",
            file_path=str(file_path),
            file_size=os.path.getsize(file_path),
            database_name=database_name,
            table_count=0,
            total_records=0,
            backup_start=now,
            backup_end=now,
            duration_seconds=0,
            status="completed",
            retention_days=30,
            created_at=now
        )

        db.add(new_backup)
        db.commit()
        db.refresh(new_backup)
        return new_backup

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo bản sao lưu: {str(e)}")

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi hệ thống khi tạo backup: {str(e)}")


# ❌ Xóa bản sao lưu (DB + file)
def delete_backup(backup_id: str, db: Session):
    """
    Xóa bản sao lưu khỏi DB và file vật lý (nếu có).
    """
    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not backup:
        raise ValueError("Không tìm thấy bản sao lưu.")

    try:
        # Xóa file vật lý nếu tồn tại
        if backup.file_path and os.path.exists(backup.file_path):
            os.remove(backup.file_path)

        db.delete(backup)
        db.commit()
        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa backup khỏi DB: {str(e)}")

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi hệ thống khi xóa backup: {str(e)}")
