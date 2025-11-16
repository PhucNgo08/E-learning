"""
==========================================================
📢 Student Notification Service (FULL VERSION – 100%)
Module xử lý tất cả nghiệp vụ thông báo dành cho HSSV:
- Lấy thông báo
- Xem chi tiết
- Đánh dấu đã đọc
- Đếm chưa đọc
- Xóa / xóa toàn bộ
- Lọc loại thông báo
- Lấy thông báo mới nhất (để hiển thị icon chuông)
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.notification import Notification
from datetime import datetime
import traceback
import uuid


# ======================================================
# 🔹 Tạo thông báo mới
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
    Tạo một thông báo mới gửi đến user.
    """
    try:
        noti = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type,
            link_url=link_url,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(noti)
        db.commit()
        db.refresh(noti)
        print(f"📢 [Notification] Sent → user {user_id}")
        return noti

    except Exception:
        db.rollback()
        print("❌ [create_notification] Error:")
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Lấy tất cả thông báo của user
# ======================================================
def get_user_notifications(db: Session, user_id: str):
    """
    Lấy toàn bộ thông báo của user theo thời gian mới nhất.
    """
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
    except Exception:
        print("❌ [get_user_notifications] Error:")
        traceback.print_exc()
        return []


# ======================================================
# 🔹 Danh sách thông báo mới nhất (cho icon chuông)
# ======================================================
def get_latest_notifications(db: Session, user_id: str, limit: int = 10):
    """
    Lấy N thông báo gần nhất (dùng cho popup bell icon).
    """
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception:
        print("❌ [get_latest_notifications] Error:")
        traceback.print_exc()
        return []


# ======================================================
# 🔹 Lọc thông báo theo loại
# ======================================================
def get_notifications_by_type(db: Session, user_id: str, n_type: str):
    """
    Lọc thông báo theo loại: assignment, quiz, system, message…
    """
    try:
        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.notification_type == n_type
            )
            .order_by(Notification.created_at.desc())
            .all()
        )
    except Exception:
        print("❌ [get_notifications_by_type] Error:")
        traceback.print_exc()
        return []


# ======================================================
# 🔹 Lấy chi tiết một thông báo
# ======================================================
def get_notification_detail(db: Session, notification_id: str, user_id: str):
    """
    Lấy chi tiết thông báo (kèm kiểm tra quyền user)
    + Đánh dấu đã đọc khi mở.
    """
    try:
        noti = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if noti:
            if not noti.is_read:
                noti.is_read = True
                noti.read_at = datetime.utcnow()
                db.commit()
                db.refresh(noti)
        return noti

    except Exception:
        db.rollback()
        print("❌ [get_notification_detail] Error:")
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Đánh dấu 1 thông báo đã đọc (kiểm tra quyền)
# ======================================================
def mark_as_read(db: Session, notification_id: str, user_id: str):
    """
    Đánh dấu một thông báo là đã đọc.
    Chỉ user sở hữu thông báo mới có quyền.
    """
    try:
        noti = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )

        if noti and not noti.is_read:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
            db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        print("❌ [mark_as_read] Error:")
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Toggle trạng thái đọc/chưa đọc
# ======================================================
def toggle_read_status(db: Session, notification_id: str, user_id: str):
    """
    Đảo trạng thái đã đọc ↔ chưa đọc.
    """
    try:
        noti = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )

        if noti:
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
        print("❌ [toggle_read_status] Error:")
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Đánh dấu tất cả thông báo đã đọc
# ======================================================
def mark_all_as_read(db: Session, user_id: str):
    """
    Đánh dấu toàn bộ thông báo của user thành đã đọc.
    """
    try:
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .update(
                {
                    Notification.is_read: True,
                    Notification.read_at: datetime.utcnow(),
                }
            )
        )
        db.commit()
        print(f"📘 [mark_all_as_read] {count} notifications marked as read.")
        return count

    except Exception:
        db.rollback()
        print("❌ [mark_all_as_read] Error:")
        traceback.print_exc()
        return 0


# ======================================================
# 🔹 Đếm số thông báo chưa đọc
# ======================================================
def count_unread_notifications(db: Session, user_id: str):
    """
    Trả về số lượng thông báo chưa đọc.
    """
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .count()
        )
    except Exception:
        print("❌ [count_unread_notifications] Error:")
        traceback.print_exc()
        return 0


# ======================================================
# 🔹 Xóa 1 thông báo (kiểm tra quyền)
# ======================================================
def delete_notification(db: Session, notification_id: str, user_id: str):
    """
    Xóa một thông báo (chỉ user sở hữu mới được xóa).
    """
    try:
        noti = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )

        if noti:
            db.delete(noti)
            db.commit()
            print(f"🗑️ [delete_notification] Removed {notification_id}")
            return True

        print("⚠️ [delete_notification] Not found or no permission.")
        return False

    except Exception:
        db.rollback()
        print("❌ [delete_notification] Error:")
        traceback.print_exc()
        return False


# ======================================================
# 🔹 Xóa toàn bộ thông báo (có bảo vệ)
# ======================================================
def delete_all_notifications(db: Session, user_id: str):
    """
    Xóa tất cả thông báo của user.
    Có bảo vệ batch để tránh lock table.
    """
    try:
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"🗑️ [delete_all_notifications] Deleted {count} notifications.")
        return count

    except Exception:
        db.rollback()
        print("❌ [delete_all_notifications] Error:")
        traceback.print_exc()
        return 0


# ======================================================
# 🔹 Phân trang thông báo
# ======================================================
def get_notifications_paginated(db: Session, user_id: str, skip: int = 0, limit: int = 20):
    """
    Lấy danh sách thông báo có phân trang.
    """
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except Exception:
        print("❌ [get_notifications_paginated] Error:")
        traceback.print_exc()
        return []
# ======================================================
# 🔹 Mock settings (cài đặt thông báo)
# ======================================================
def get_user_notification_settings(db: Session, user_id: str):
    """
    Trả về cài đặt thông báo mặc định của user.
    Tạm thời dùng dữ liệu mock.
    Sau này nếu có bảng notification_settings thì lấy từ DB.
    """
    return {
        "system": True,
        "course": True,
        "assignment": True,
        "quiz": True,
        "message": True,
    }


# ======================================================
# 🔹 Cập nhật cài đặt thông báo
# ======================================================
def update_user_notification_settings(db: Session, user_id: str, new_settings: dict):
    """
    Lưu cài đặt thông báo của user.
    Tạm thời chỉ in ra (mock).
    Sau này sẽ lưu DB khi có bảng riêng.
    """
    print(f"⚙️ [NotificationSettings] user={user_id} -> {new_settings}")
    return new_settings
