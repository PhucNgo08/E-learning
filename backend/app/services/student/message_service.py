"""
==========================================================
📘 SERVICE: Message (Student ↔ Teacher)
FULL VERSION 2025 – Hỗ trợ 2 role
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.message import Message
from app.models.user import User
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import os
import traceback

# 🔔 Import Notification
from app.services.student.notification_service import create_notification


# ======================================================
# 📥 Hộp thư đến (Receiver)
# ======================================================
def get_inbox_messages(db: Session, user_id: str):
    """Trả về danh sách tin nhắn mà user nhận được."""

    try:
        return (
            db.query(Message)
            .filter(Message.receiver_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception:
        traceback.print_exc()
        return []


# ======================================================
# 📤 Hộp thư đã gửi (Sender)
# ======================================================
def get_sent_messages(db: Session, user_id: str):
    """Trả về danh sách tin nhắn mà user đã gửi."""

    try:
        return (
            db.query(Message)
            .filter(Message.sender_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception:
        traceback.print_exc()
        return []


# ======================================================
# 📨 GỬI TIN NHẮN (có file) + Notification theo ROLE
# ======================================================
def send_message(db: Session, sender_id: str, receiver_id: str, content: str, attachment=None):
    """
    Gửi tin nhắn từ sender → receiver.
    Nếu có file đính kèm sẽ upload và lưu metadata.
    Tự động tạo thông báo "Tin nhắn mới" theo ROLE người nhận.
    """

    try:
        if not content and not (attachment and attachment.filename):
            return None  # Không gửi tin rỗng

        uploads_dir = Path("uploads/messages")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        attachment_url = None
        attachment_name = None
        attachment_size = None

        # ==============================================
        # 📎 Upload file đính kèm
        # ==============================================
        if attachment and attachment.filename:
            safe_name = attachment.filename.replace(" ", "_")
            filename = f"{uuid.uuid4().hex}_{safe_name}"
            file_path = uploads_dir / filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            attachment_url = f"/uploads/messages/{filename}"
            attachment_name = safe_name
            attachment_size = os.path.getsize(file_path)

        # ==============================================
        # 📨 Tạo tin nhắn
        # ==============================================
        msg = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=(content or "").strip(),
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_size=attachment_size,
            sent_at=datetime.utcnow(),
        )

        db.add(msg)
        db.commit()
        db.refresh(msg)

        # ==============================================
        # 🎯 Lấy role người nhận
        # ==============================================
        receiver = db.query(User).filter(User.id == receiver_id).first()

        if receiver:
            # Chọn đúng prefix link tùy role
            prefix = "/student" if receiver.role == "student" else "/teacher"
            link = f"{prefix}/message/view/{msg.id}"

            preview = (content or "(Tệp đính kèm)")[:80]

            # 🔔 Gửi thông báo
            create_notification(
                db=db,
                user_id=receiver_id,
                title="📩 Tin nhắn mới",
                message=f"Bạn có tin nhắn mới từ người dùng {sender_id}: \"{preview}\"",
                notification_type="message",
                link_url=link
            )

        return msg

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


# ======================================================
# 🔍 Chi tiết tin nhắn
# ======================================================
def get_message_detail(db: Session, message_id: str):
    try:
        return db.query(Message).filter(Message.id == message_id).first()
    except Exception:
        traceback.print_exc()
        return None


# ======================================================
# 🗑 Xóa tin nhắn
# ======================================================
def delete_message(db: Session, message_id: str, user_id: str):
    """
    Xóa tin nhắn (chỉ người gửi hoặc người nhận).
    Xóa file nếu có.
    """

    try:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            return False

        # Check quyền
        if msg.sender_id != user_id and msg.receiver_id != user_id:
            return False

        # Xóa file vật lý nếu có
        if msg.attachment_url:
            physical_file = Path(msg.attachment_url.lstrip("/"))
            if physical_file.exists():
                try:
                    os.remove(physical_file)
                except:
                    pass  # Không crash hệ thống

        # Xóa record DB
        db.delete(msg)
        db.commit()
        return True

    except Exception:
        db.rollback()
        traceback.print_exc()
        return False
