"""
==========================================================
📢 SERVICE: Notification Service (Teacher)
Quản lý tạo, lấy, đánh dấu đọc thông báo cho người dùng
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from app.models.notification import Notification


# ======================================================
# 📨 1️⃣ Tạo thông báo mới
# ======================================================
def create_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str = None
):
    """
    Tạo một thông báo mới cho người dùng
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
        created_at=datetime.utcnow(),
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


# ======================================================
# 📬 2️⃣ Lấy danh sách thông báo theo người dùng
# ======================================================
def get_notifications_by_user(db: Session, user_id: str, limit: int = 20):
    """
    Lấy danh sách thông báo gần nhất của người dùng
    """
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at))
        .limit(limit)
        .all()
    )


# ======================================================
# 🔍 3️⃣ Lấy chi tiết 1 thông báo
# ======================================================
def get_notification_detail(db: Session, notification_id: str, user_id: str):
    """
    Lấy chi tiết thông báo (chỉ khi thuộc về user)
    """
    return (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )


# ======================================================
# ✅ 4️⃣ Đánh dấu là đã đọc
# ======================================================
def mark_as_read(db: Session, notification_id: str, user_id: str):
    """
    Đánh dấu một thông báo là đã đọc
    """
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )

    if not notification:
        return None

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    return notification


# ======================================================
# 🧹 5️⃣ Xóa thông báo (nếu cần)
# ======================================================
def delete_notification(db: Session, notification_id: str, user_id: str):
    """
    Xóa một thông báo của người dùng (tuỳ chọn)
    """
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notification:
        return False

    db.delete(notification)
    db.commit()
    return True
