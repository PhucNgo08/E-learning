from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> dict:
    title = (title or "").strip()
    message = (message or "").strip()
    notification_type = (notification_type or "system").strip() or "system"
    link_url = (link_url or "").strip() or None

    if not user_id:
        return {"success": False, "error": "Thiếu user_id."}
    if not title:
        return {"success": False, "error": "Tiêu đề thông báo không được để trống."}
    if not message:
        return {"success": False, "error": "Nội dung thông báo không được để trống."}

    try:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            link_url=link_url,
            created_at=datetime.utcnow(),
            is_read=False,
            read_at=None,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return {"success": True, "notification": notification}

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:create_notification] Lỗi:", e)
        return {"success": False, "error": str(e)}


def get_notifications_by_user(
    db: Session,
    user_id: str,
    limit: int = 100,
) -> list[Notification]:
    try:
        if not user_id:
            return []

        limit = max(1, min(limit or 100, 200))

        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .all()
        )

    except Exception as e:
        print("❌ [Teacher:get_notifications_by_user] Lỗi:", e)
        return []


def get_latest_notifications(
    db: Session,
    user_id: str,
    limit: int = 5,
) -> list[Notification]:
    try:
        if not user_id:
            return []

        limit = max(1, min(limit or 5, 20))

        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .all()
        )

    except Exception as e:
        print("❌ [Teacher:get_latest_notifications] Lỗi:", e)
        return []


def count_unread_notifications(
    db: Session,
    user_id: str,
) -> int:
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

    except Exception as e:
        print("❌ [Teacher:count_unread_notifications] Lỗi:", e)
        return 0


def get_notification_for_user(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
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

    except Exception as e:
        print("❌ [Teacher:get_notification_for_user] Lỗi:", e)
        return None


def get_notification_detail(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    return get_notification_for_user(
        db=db,
        notification_id=notification_id,
        user_id=user_id,
    )


def mark_as_read(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    try:
        notification = get_notification_for_user(
            db=db,
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)

        return notification

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:mark_as_read] Lỗi:", e)
        return None


def mark_all_as_read_by_user(
    db: Session,
    user_id: str,
) -> int:
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

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:mark_all_as_read_by_user] Lỗi:", e)
        return 0


def mark_all_as_read(
    db: Session,
    user_id: str,
) -> int:
    return mark_all_as_read_by_user(db=db, user_id=user_id)


def toggle_read_status(
    db: Session,
    notification_id: str,
    user_id: str,
) -> Notification | None:
    try:
        notification = get_notification_for_user(
            db=db,
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return None

        if notification.is_read:
            notification.is_read = False
            notification.read_at = None
        else:
            notification.is_read = True
            notification.read_at = datetime.utcnow()

        db.commit()
        db.refresh(notification)

        return notification

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:toggle_read_status] Lỗi:", e)
        return None


def delete_notification(
    db: Session,
    notification_id: str,
    user_id: str,
) -> bool:
    try:
        notification = get_notification_for_user(
            db=db,
            notification_id=notification_id,
            user_id=user_id,
        )

        if not notification:
            return False

        db.delete(notification)
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:delete_notification] Lỗi:", e)
        return False


def delete_all_notifications(
    db: Session,
    user_id: str,
) -> int:
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

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:delete_all_notifications] Lỗi:", e)
        return 0