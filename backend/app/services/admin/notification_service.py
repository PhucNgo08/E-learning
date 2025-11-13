"""
==========================================================
📢 SERVICE: Notification Management
Quản lý CRUD thông báo hệ thống
==========================================================
"""
from sqlalchemy.orm import Session
from app.models.notification import Notification
from datetime import datetime
import uuid


def get_all_notifications(db: Session):
    return db.query(Notification).order_by(Notification.created_at.desc()).all()


def create_notification(db: Session, user_id: str, title: str, message: str, notification_type: str = "system", link_url: str = None):
    new_noti = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
        created_at=datetime.utcnow(),
        is_read=0
    )
    db.add(new_noti)
    db.commit()
    db.refresh(new_noti)
    return new_noti


def mark_as_read(db: Session, noti_id: str):
    noti = db.query(Notification).filter(Notification.id == noti_id).first()
    if noti:
        noti.is_read = 1
        noti.read_at = datetime.utcnow()
        db.commit()
        return True
    return False


def delete_notification(db: Session, noti_id: str):
    noti = db.query(Notification).filter(Notification.id == noti_id).first()
    if not noti:
        return None
    db.delete(noti)
    db.commit()
    return noti
