"""
==========================================================
📘 SERVICE: Teacher - Message (Tin nhắn nội bộ)
Xử lý logic gửi, nhận và hiển thị tin nhắn
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.message import Message
from datetime import datetime
from pathlib import Path
import uuid
import shutil


# ======================================================
# 📥 Hộp thư đến (Receiver)
# ======================================================
def get_inbox_messages(db: Session, user_id: str):
    """Lấy tin nhắn đến (receiver_id = user_id)"""
    try:
        return (
            db.query(Message)
            .filter(Message.receiver_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [Teacher:get_inbox_messages] Lỗi:", e)
        return []


# ======================================================
# 📤 Hộp thư đã gửi (Sender)
# ======================================================
def get_sent_messages(db: Session, user_id: str):
    """Lấy tin nhắn đã gửi (sender_id = user_id)"""
    try:
        return (
            db.query(Message)
            .filter(Message.sender_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [Teacher:get_sent_messages] Lỗi:", e)
        return []


# ======================================================
# 📬 Gửi tin nhắn (có hỗ trợ file đính kèm)
# ======================================================
def send_message(db: Session, sender_id: str, receiver_id: str, content: str, attachment=None):
    """
    Gửi tin nhắn từ giáo viên → người nhận.
    Nếu có file đính kèm, lưu file và ghi lại đường dẫn.
    """
    try:
        attachment_url = None
        attachment_name = None
        attachment_size = None

        # ✅ Nếu có file upload
        if attachment:
            uploads_dir = Path("uploads/messages")
            uploads_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{uuid.uuid4().hex}_{attachment.filename}"
            file_path = uploads_dir / filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            attachment_url = str(file_path)
            attachment_name = attachment.filename
            attachment_size = f"{round(file_path.stat().st_size / 1024, 2)} KB"
            print(f"📎 [Teacher:send_message] Đã lưu file: {attachment_url}")

        # ✅ Tạo bản ghi tin nhắn
        msg = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content.strip(),
            sent_at=datetime.utcnow(),
        )

        # Nếu model có cột file đính kèm, gán thông tin
        if hasattr(Message, "attachment_url"):
            msg.attachment_url = attachment_url
            msg.attachment_name = attachment_name
            msg.attachment_size = attachment_size

        db.add(msg)
        db.commit()
        db.refresh(msg)

        print(f"✅ [Teacher:send_message] {sender_id} ➜ {receiver_id}")
        return msg

    except Exception as e:
        db.rollback()
        print("❌ [Teacher:send_message] Lỗi:", e)
        return None


# ======================================================
# 🔍 Lấy chi tiết tin nhắn
# ======================================================
def get_message_detail(db: Session, message_id: str):
    """Trả về chi tiết 1 tin nhắn cụ thể"""
    try:
        return db.query(Message).filter(Message.id == message_id).first()
    except Exception as e:
        print("❌ [Teacher:get_message_detail] Lỗi:", e)
        return None
