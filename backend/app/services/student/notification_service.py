"""
==========================================================
📢 Service: Notifications (Student)
Xử lý dữ liệu thông báo sinh viên
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.notification import Notification
from datetime import datetime
import traceback


# ======================================================
# 🔹 Lấy tất cả thông báo của sinh viên
# ======================================================
def get_student_notifications(db: Session, user_id: str):
    """Lấy tất cả thông báo của sinh viên."""
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_student_notifications] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 🔹 Lấy chi tiết 1 thông báo
# ======================================================
def get_notification_by_id(db: Session, notification_id: str):
    """Lấy chi tiết 1 thông báo."""
    try:
        return db.query(Notification).filter(Notification.id == notification_id).first()
    except Exception as e:
        print("❌ [get_notification_by_id] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Đánh dấu 1 thông báo đã đọc
# ======================================================
def mark_as_read(db: Session, notification_id: str):
    """Đánh dấu 1 thông báo là đã đọc."""
    try:
        noti = db.query(Notification).filter(Notification.id == notification_id).first()
        if noti and not noti.is_read:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
            db.refresh(noti)
        return noti
    except Exception as e:
        db.rollback()
        print("❌ [mark_as_read] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🔹 Đánh dấu tất cả thông báo là đã đọc
# ======================================================
def mark_all_as_read(db: Session, user_id: str):
    """Đánh dấu toàn bộ thông báo của sinh viên là đã đọc."""
    try:
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .update({
                Notification.is_read: True,
                Notification.read_at: datetime.utcnow()
            })
        )
        db.commit()
        print(f"✅ [mark_all_as_read] {count} thông báo đã được đánh dấu là đã đọc.")
        return count
    except Exception as e:
        db.rollback()
        print("❌ [mark_all_as_read] Lỗi:", e)
        traceback.print_exc()
        return 0


# ======================================================
# 🔹 Xóa 1 thông báo
# ======================================================
def delete_notification(db: Session, notification_id: str, user_id: str):
    """Xóa một thông báo (chỉ nếu thuộc về sinh viên đó)."""
    try:
        noti = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if noti:
            db.delete(noti)
            db.commit()
            print(f"🗑️ [delete_notification] Đã xóa thông báo {notification_id}")
            return True
        else:
            print("⚠️ [delete_notification] Không tìm thấy thông báo hoặc không có quyền.")
            return False
    except Exception as e:
        db.rollback()
        print("❌ [delete_notification] Lỗi:", e)
        traceback.print_exc()
        return False


# ======================================================
# 🔹 Đếm số thông báo chưa đọc (optional)
# ======================================================
def count_unread_notifications(db: Session, user_id: str):
    """Đếm số thông báo chưa đọc."""
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .count()
        )
    except Exception as e:
        print("❌ [count_unread_notifications] Lỗi:", e)
        traceback.print_exc()
        return 0


# ======================================================
# ⚙️ Cấu hình nhận thông báo của user (mock)
# ======================================================
def get_user_notification_settings(db: Session, user_id: str):
    """Giả lập dữ liệu cài đặt thông báo (tùy chỉnh sau nếu có bảng riêng)."""
    return {
        "system": True,
        "course": True,
        "assignment": True,
        "quiz": True,
        "message": False,
    }


def update_user_notification_settings(db: Session, user_id: str, new_settings: dict):
    """Giả lập cập nhật dữ liệu cài đặt thông báo."""
    print(f"✅ [update_user_notification_settings] user={user_id}, settings={new_settings}")
    return new_settings
    try:
        discussion.content = new_content.strip()
        discussion.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(discussion)
        return discussion
    except Exception as e:
        db.rollback()
        print("❌ [update_discussion] Lỗi:", e)
        traceback.print_exc()
        return {"error": "Không thể cập nhật bài thảo luận."}
# ==========================================================