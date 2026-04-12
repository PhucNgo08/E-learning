"""
==========================================================
📢 SERVICE: Notification Service (Teacher)
Quản lý tạo, lấy, đánh dấu đọc thông báo cho người dùng
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import uuid

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
    link_url: str | None = None
):
    """
    Tạo một thông báo mới cho người dùng
    """
    title = (title or "").strip()
    message = (message or "").strip()

    if not user_id:
        return {"error": "Thiếu user_id."}
    if not title:
        return {"error": "Tiêu đề thông báo không được để trống."}
    if not message:
        return {"error": "Nội dung thông báo không được để trống."}

    try:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type or "system",
            link_url=link_url,
            created_at=datetime.utcnow(),
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return {"success": True, "notification": notification}

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:create_notification] Lỗi:", e)
        return {"error": str(e)}


# ======================================================
# 📬 2️⃣ Lấy danh sách thông báo theo người dùng
# ======================================================
def get_notifications_by_user(db: Session, user_id: str, limit: int = 20):
    """
    Lấy danh sách thông báo gần nhất của người dùng
    """
    try:
        limit = max(1, min(limit or 20, 100))
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


# ======================================================
# 🔍 3️⃣ Lấy chi tiết 1 thông báo
# ======================================================
def get_notification_detail(db: Session, notification_id: str, user_id: str):
    """
    Lấy chi tiết thông báo (chỉ khi thuộc về user)
    """
    try:
        return (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
    except Exception as e:
        print("❌ [Teacher:get_notification_detail] Lỗi:", e)
        return None


# ======================================================
# ✅ 4️⃣ Đánh dấu là đã đọc
# ======================================================
def mark_as_read(db: Session, notification_id: str, user_id: str):
    """
    Đánh dấu một thông báo là đã đọc
    """
    try:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
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


# ======================================================
# 🧹 5️⃣ Xóa thông báo
# ======================================================
def delete_notification(db: Session, notification_id: str, user_id: str):
    """
    Xóa một thông báo của người dùng
    """
    try:
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

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:delete_notification] Lỗi:", e)
        return False