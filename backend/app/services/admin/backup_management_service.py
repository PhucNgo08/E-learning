from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, time
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.backup_history import BackupHistory
from app.models.backup_schedule import BackupSchedule


# Thư mục lưu backup: ưu tiên env BACKUP_DIR, nếu không thì dùng thư mục backups trong backend
_DEFAULT_BACKUP_DIR = Path(__file__).resolve().parents[3] / "backups"
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(_DEFAULT_BACKUP_DIR)))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

VALID_BACKUP_TYPES = {"full", "incremental"}
VALID_FREQUENCIES = {"daily", "weekly", "monthly"}


def _normalize_backup_type(value: str | None) -> str:
    value = (value or "full").strip().lower()
    if value not in VALID_BACKUP_TYPES:
        raise ValueError("Loại backup không hợp lệ.")
    return value


def _normalize_frequency(value: str | None) -> str:
    value = (value or "daily").strip().lower()
    if value not in VALID_FREQUENCIES:
        raise ValueError("Tần suất backup không hợp lệ.")
    return value


def _safe_database_name(value: str | None) -> str:
    value = (value or "e_learning").strip()
    if not value:
        raise ValueError("Tên database không được để trống.")
    return value


# ============================================================
# 1) Lấy danh sách tất cả backup
# ============================================================
def get_all_backups(db: Session):
    try:
        return (
            db.query(BackupHistory)
            .order_by(BackupHistory.created_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách backup: {str(e)}") from e


def get_backup_by_id(backup_id: str, db: Session):
    try:
        return (
            db.query(BackupHistory)
            .filter(BackupHistory.id == backup_id)
            .first()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy thông tin backup: {str(e)}") from e


# ============================================================
# 2) Tạo backup (tạo file + ghi DB)
# ============================================================
def create_backup(
    database_name: str,
    backup_type: str,
    db: Session,
    note: str | None = None,
):
    try:
        now = datetime.now()
        database_name = _safe_database_name(database_name)
        backup_type = _normalize_backup_type(backup_type)

        file_name = f"{database_name}_{backup_type}_{now.strftime('%Y%m%d_%H%M%S')}.sql"
        file_path = BACKUP_DIR / file_name

        # Giả lập file backup
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"-- Backup database: {database_name}\n")
            f.write(f"-- Backup type: {backup_type}\n")
            f.write(f"-- Created at: {now.isoformat(sep=' ', timespec='seconds')}\n")
            if note and note.strip():
                f.write(f"-- Note: {note.strip()}\n")
            f.write("\n-- SQL dump content placeholder\n")

        new_backup = BackupHistory(
            id=str(uuid.uuid4()),
            backup_type=backup_type,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            database_name=database_name,
            table_count=0,
            total_records=0,
            backup_start=now,
            backup_end=now,
            duration_seconds=0,
            status="completed",
            retention_days=30,
            created_at=now,
        )

        db.add(new_backup)
        db.commit()
        db.refresh(new_backup)
        return new_backup

    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo backup: {str(e)}") from e


# ============================================================
# 3) Xoá backup (DB + file vật lý)
# ============================================================
def delete_backup(backup_id: str, db: Session):
    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not backup:
        raise ValueError("Không tìm thấy bản sao lưu.")

    try:
        if backup.file_path:
            file_path = Path(backup.file_path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()

        db.delete(backup)
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa backup: {str(e)}") from e


# ============================================================
# 4) Danh sách lịch backup
# ============================================================
def get_all_backup_schedules(db: Session):
    try:
        return (
            db.query(BackupSchedule)
            .order_by(BackupSchedule.created_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách lịch backup: {str(e)}") from e


def get_backup_schedule_by_id(schedule_id: str, db: Session):
    try:
        return (
            db.query(BackupSchedule)
            .filter(BackupSchedule.id == schedule_id)
            .first()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy chi tiết lịch backup: {str(e)}") from e


# ============================================================
# 5) Tạo lịch backup
# ============================================================
def create_backup_schedule(
    schedule_name: str,
    schedule_type: str,
    freq: str,
    retention_days: int,
    db: Session,
):
    try:
        schedule_name = (schedule_name or "").strip()
        if not schedule_name:
            raise ValueError("Tên lịch backup không được để trống.")

        schedule_type = _normalize_backup_type(schedule_type)
        freq = _normalize_frequency(freq)

        try:
            retention_days = int(retention_days)
        except (TypeError, ValueError):
            raise ValueError("Retention days không hợp lệ.")

        if retention_days < 1 or retention_days > 365:
            raise ValueError("Retention days phải trong khoảng 1 đến 365.")

        existing = (
            db.query(BackupSchedule)
            .filter(BackupSchedule.schedule_name == schedule_name)
            .first()
        )
        if existing:
            raise ValueError("Tên lịch backup đã tồn tại.")

        new_schedule = BackupSchedule(
            id=str(uuid.uuid4()),
            schedule_name=schedule_name,
            backup_type=schedule_type,
            frequency=freq,
            frequency_detail=None,
            preferred_start_time=time(2, 0, 0),
            max_duration_minutes=240,
            retention_days=retention_days,
            keep_last_n=10,
            notify_on_success=False,
            notify_on_failure=True,
            notification_emails=None,
            is_active=True,
            last_run=None,
            last_status="success",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        return new_schedule

    except ValueError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo lịch sao lưu: {str(e)}") from e


# ============================================================
# 6) Xoá lịch backup
# ============================================================
def delete_backup_schedule(schedule_id: str, db: Session):
    schedule = db.query(BackupSchedule).filter(BackupSchedule.id == schedule_id).first()
    if not schedule:
        raise ValueError("Không tìm thấy lịch backup.")

    try:
        db.delete(schedule)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa lịch backup: {str(e)}") from e


# ============================================================
# 7) Dọn backup cũ
# ============================================================
def cleanup_old_backups(db: Session):
    """
    Dọn backup cũ dựa trên retention_days của từng bản ghi.
    Xóa cả file vật lý lẫn bản ghi DB.
    """
    try:
        backups = db.query(BackupHistory).all()
        now = datetime.now()
        deleted_count = 0

        for backup in backups:
            if not backup.backup_start or not backup.retention_days:
                continue

            expire_at = backup.backup_start + timedelta(days=int(backup.retention_days))
            if expire_at >= now:
                continue

            if backup.file_path:
                file_path = Path(backup.file_path)
                if file_path.exists() and file_path.is_file():
                    try:
                        file_path.unlink()
                    except OSError:
                        pass

            db.delete(backup)
            deleted_count += 1

        db.commit()
        return {
            "deleted_count": deleted_count,
            "message": f"Đã dọn {deleted_count} backup cũ.",
        }

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi dọn backup cũ: {str(e)}") from e