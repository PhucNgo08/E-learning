"""
📢 Service: Notifications (Student)
Xử lý dữ liệu thông báo sinh viên
"""

from sqlalchemy.orm import Session
from app.models.notification import Notification
from datetime import datetime
import uuid


def get_student_notifications(db: Session, user_id: str):
    """Lấy tất cả thông báo của sinh viên"""
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_notification_by_id(db: Session, notification_id: str):
    """Lấy chi tiết 1 thông báo"""
    return db.query(Notification).filter(Notification.id == notification_id).first()


def mark_as_read(db: Session, notification_id: str):
    """Đánh dấu thông báo đã đọc"""
    noti = db.query(Notification).filter(Notification.id == notification_id).first()
    if noti and not noti.is_read:
        noti.is_read = True
        noti.read_at = datetime.utcnow()
        db.commit()
    return noti


# ⚙️ Tùy chọn: lưu cấu hình nhận thông báo của user
def get_user_notification_settings(db: Session, user_id: str):
    """Giả lập dữ liệu cài đặt thông báo (tùy chỉnh sau nếu có bảng riêng)"""
    return {
        "system": True,
        "course": True,
        "assignment": True,
        "quiz": True,
        "message": False,
    }
