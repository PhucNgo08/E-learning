from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.models.backup_history import BackupHistory
from datetime import datetime
import uuid
import os
from pathlib import Path

# 🧭 Thư mục lưu file backup vật lý
BACKUP_DIR = Path("D:/KhoaHoctructuyen/KHoaHocOnline/backend/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 📋 Lấy danh sách tất cả backup
# ============================================================
def get_all_backups(db: Session):
    try:
        return (
            db.query(BackupHistory)
            .order_by(BackupHistory.created_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách backup: {str(e)}")


# ============================================================
# 💾 Tạo backup (tạo file + ghi vào DB)
# ============================================================
def create_backup(database_name: str, backup_type: str, db: Session):
    try:
        now = datetime.now()
        file_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}.sql"
        file_path = BACKUP_DIR / file_name

        # Giả lập file backup
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"-- Backup của database: {database_name}\n")
            f.write(f"-- Thời gian: {now}\n")

        # Ghi DB
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

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo backup: {str(e)}")


# ============================================================
# ❌ Xoá backup (DB + file hệ thống)
# ============================================================
def delete_backup(backup_id: str, db: Session):
    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not backup:
        raise ValueError("Không tìm thấy bản sao lưu.")

    try:
        if backup.file_path and os.path.exists(backup.file_path):
            os.remove(backup.file_path)

        db.delete(backup)
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa backup: {str(e)}")


# ============================================================
# 🆕 ① Gọi Stored Procedure: Tạo lịch backup
# ============================================================
def create_backup_schedule(schedule_name: str, schedule_type: str, freq: str, retention_days: int, db: Session):
    """
    Gọi stored procedure: sp_create_backup_schedule
    """
    try:
        db.execute(
            text("""
                CALL sp_create_backup_schedule(
                    :schedule_name,
                    :schedule_type,
                    :frequency,
                    :retention_days
                )
            """),
            {
                "schedule_name": schedule_name,
                "schedule_type": schedule_type,   # 'full' hoặc 'incremental'
                "frequency": freq,               # 'daily' / 'weekly' / 'monthly'
                "retention_days": retention_days
            }
        )
        db.commit()
        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo lịch sao lưu: {str(e)}")


# ============================================================
# 🆕 ② Gọi Stored Procedure: Dọn backup cũ
# ============================================================
def cleanup_old_backups(db: Session):
    """
    Gọi stored procedure: sp_cleanup_old_backups
    """
    try:
        result = db.execute(text("CALL sp_cleanup_old_backups()"))
        db.commit()

        # Lấy message từ stored procedure
        return list(result)

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi dọn backup cũ: {str(e)}")
