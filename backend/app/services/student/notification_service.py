"""
==========================================================
📢 Student Notification Service
Quản lý thông báo sinh viên
- Tạo thông báo
- Lấy danh sách thông báo
- Lấy thông báo mới nhất
- Đếm thông báo chưa đọc
- Đánh dấu đã đọc / chưa đọc
- Xóa thông báo
- Cài đặt thông báo cơ bản
==========================================================
"""

from __future__ import annotations

from datetime import datetime
import traceback
import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification


# ======================================================
# CREATE
# ======================================================
def create_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> Notification | None:
    """
    Tạo thông báo mới cho sinh viên.
    """
    try:
        title = (title or "").strip()
        message = (message or "").strip()
        notification_type = (notification_type or "system").strip() or "system"
        link_url = (link_url or "").strip() or None

        if not user_id or not title or not message:
            return None

        noti = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link_url=link_url,
            is_read=False,
            read_at=None,
            created_at=datetime.utcnow(),
        )

        db.add(noti)
        db.commit()
        db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


# ======================================================
# GET
# ======================================================
def get_user_notifications(db: Session, user_id: str) -> list[Notification]:
    """
    Lấy toàn bộ thông báo của sinh viên.
    """
    try:
        if not user_id:
            return []

        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    except Exception:
        traceback.print_exc()
        return []


def get_latest_notifications(
    db: Session,
    user_id: str,
    limit: int = 5,
) -> list[Notification]:
    """
    Lấy thông báo mới nhất để hiển thị trên chuông.
    """
    try:
        if not user_id:
            return []

        limit = max(1, min(limit or 5, 20))

        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )

    except Exception:
        traceback.print_exc()
        return []


def get_notifications_by_type(
    db: Session,
    user_id: str,
    n_type: str,
) -> list[Notification]:
    """
    Lấy thông báo theo loại: system, course, assignment, quiz, message.
    """
    try:
        if not user_id or not n_type:
            return []

        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.notification_type == n_type,
            )
            .order_by(Notification.created_at.desc())
            .all()
        )

    except Exception:
        traceback.print_exc()
        return []


def get_notification_for_user(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    """
    Lấy 1 thông báo thuộc đúng sinh viên hiện tại.
    """
    try:
        if not notification_id or not user_id:
            return None

        return (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )

    except Exception:
        traceback.print_exc()
        return None


def get_notification_detail(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    """
    Lấy chi tiết thông báo và tự đánh dấu đã đọc.
    """
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if not noti:
            return None

        if not noti.is_read:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
            db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def get_notifications_paginated(
    db: Session,
    user_id: str,
    skip: int = 0,
    limit: int = 20,
) -> list[Notification]:
    """
    Lấy thông báo có phân trang nếu cần mở rộng sau này.
    """
    try:
        if not user_id:
            return []

        skip = max(skip or 0, 0)
        limit = max(1, min(limit or 20, 100))

        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    except Exception:
        traceback.print_exc()
        return []


# ======================================================
# COUNT
# ======================================================
def count_unread_notifications(db: Session, user_id: str) -> int:
    """
    Đếm thông báo chưa đọc để hiện badge đỏ trên icon chuông.
    """
    try:
        if not user_id:
            return 0

        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .count()
        )

    except Exception:
        traceback.print_exc()
        return 0


# ======================================================
# UPDATE
# ======================================================
def mark_as_read(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    """
    Đánh dấu 1 thông báo là đã đọc.
    """
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if not noti:
            return None

        if not noti.is_read:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
            db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def toggle_read_status(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    """
    Đổi trạng thái đọc/chưa đọc.
    """
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if not noti:
            return None

        if noti.is_read:
            noti.is_read = False
            noti.read_at = None
        else:
            noti.is_read = True
            noti.read_at = datetime.utcnow()

        db.commit()
        db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def mark_all_as_read(db: Session, user_id: str) -> int:
    """
    Đánh dấu tất cả thông báo của sinh viên là đã đọc.
    """
    try:
        if not user_id:
            return 0

        count = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .update(
                {
                    Notification.is_read: True,
                    Notification.read_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
        )

        db.commit()
        return count

    except Exception:
        db.rollback()
        traceback.print_exc()
        return 0


# ======================================================
# DELETE
# ======================================================
def delete_notification(
    db: Session,
    notification_id: str,
    user_id: str,
) -> bool:
    """
    Xóa 1 thông báo của sinh viên.
    """
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if not noti:
            return False

        db.delete(noti)
        db.commit()

        return True

    except Exception:
        db.rollback()
        traceback.print_exc()
        return False


def delete_all_notifications(db: Session, user_id: str) -> int:
    """
    Xóa toàn bộ thông báo của sinh viên.
    """
    try:
        if not user_id:
            return 0

        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .delete(synchronize_session=False)
        )

        db.commit()
        return count

    except Exception:
        db.rollback()
        traceback.print_exc()
        return 0


# ======================================================
# SETTINGS
# ======================================================
def get_user_notification_settings(db: Session, user_id: str) -> dict:
    """
    Cài đặt thông báo mô phỏng.
    Hiện tại chưa có bảng riêng nên trả về mặc định.
    """
    return {
        "system": True,
        "course": True,
        "assignment": True,
        "quiz": True,
        "message": True,
    }


def update_user_notification_settings(
    db: Session,
    user_id: str,
    new_settings: dict,
) -> dict:
    """
    Lưu cài đặt thông báo mô phỏng.
    Nếu sau này có bảng notification_settings thì cập nhật tại đây.
    """
    return new_settings