"""
📗 Service: Notification (Thông báo)
"""

from sqlalchemy.orm import Session
from app.models.notification import Notification
from datetime import datetime
import uuid

def get_student_notifications(db: Session, user_id: str):
    """Lấy danh sách thông báo"""
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()

def mark_as_read(db: Session, notification_id: str):
    """Đánh dấu thông báo đã đọc"""
    noti = db.query(Notification).filter(Notification.id == notification_id).first()
    if noti:
        noti.is_read = True
        noti.read_at = datetime.utcnow()
        db.commit()
    return noti
