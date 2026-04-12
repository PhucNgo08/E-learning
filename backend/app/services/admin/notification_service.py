"""
==========================================================
📢 SERVICE: Notification Management
Quản lý CRUD thông báo hệ thống
==========================================================
"""
from datetime import datetime
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notification import Notification


def get_all_notifications(db: Session) -> list[Notification]:
    return db.query(Notification).order_by(Notification.created_at.desc()).all()


def get_notification_by_id(db: Session, noti_id: str) -> Notification | None:
    return db.query(Notification).filter(Notification.id == noti_id).first()


def create_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> Notification:
    title = (title or "").strip()
    message = (message or "").strip()
    link_url = (link_url or "").strip() or None

    new_noti = Notification(
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

    try:
        db.add(new_noti)
        db.commit()
        db.refresh(new_noti)
        return new_noti
    except SQLAlchemyError:
        db.rollback()
        raise


def mark_as_read(db: Session, noti_id: str) -> bool:
    noti = get_notification_by_id(db, noti_id)
    if not noti:
        return False

    if not noti.is_read:
        try:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise

    return True


def delete_notification(db: Session, noti_id: str) -> Notification | None:
    noti = get_notification_by_id(db, noti_id)
    if not noti:
        return None

    try:
        db.delete(noti)
        db.commit()
        return noti
    except SQLAlchemyError:
        db.rollback()
        raise