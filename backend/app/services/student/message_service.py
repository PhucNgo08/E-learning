"""
==========================================================
📘 SERVICE: Student - Message (Tin nhắn nội bộ)
Xử lý logic gửi, nhận và hiển thị tin nhắn
==========================================================
"""
from sqlalchemy.orm import Session
from app.models.message import Message
from datetime import datetime
from pathlib import Path
import uuid
import shutil
import os
import traceback


# ======================================================
# 📥 Hộp thư đến (Receiver)
# ======================================================
def get_inbox_messages(db: Session, user_id: str):
    """Lấy tin nhắn đến (receiver_id = user_id)."""
    try:
        return (
            db.query(Message)
            .filter(Message.receiver_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_inbox_messages] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 📤 Hộp thư đã gửi (Sender)
# ======================================================
def get_sent_messages(db: Session, user_id: str):
    """Lấy tin nhắn đã gửi (sender_id = user_id)."""
    try:
        return (
            db.query(Message)
            .filter(Message.sender_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_sent_messages] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 📬 Gửi tin nhắn (có hỗ trợ file đính kèm)
# ======================================================
def send_message(db: Session, sender_id: str, receiver_id: str, content: str, attachment=None):
    """
    Gửi tin nhắn từ sender → receiver.
    Nếu có file đính kèm, lưu file và ghi lại đường dẫn.
    """
    try:
        uploads_dir = Path("uploads/messages")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        attachment_url = None
        attachment_name = None
        attachment_size = None

        # ✅ Nếu có file upload
        if attachment:
            filename = f"{uuid.uuid4().hex}_{attachment.filename}"
            file_path = uploads_dir / filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            attachment_url = str(file_path)
            attachment_name = attachment.filename
            attachment_size = os.path.getsize(file_path)
            print(f"📎 [send_message] Đã lưu file: {attachment_url}")

        # ✅ Tạo bản ghi tin nhắn
        msg = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=(content or "").strip(),
            sent_at=datetime.utcnow(),
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_size=attachment_size
        )

        db.add(msg)
        db.commit()
        db.refresh(msg)

        print(f"✅ [send_message] {sender_id} ➜ {receiver_id}")
        return msg

    except Exception as e:
        db.rollback()
        print("❌ [send_message] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🔍 Lấy chi tiết tin nhắn
# ======================================================
def get_message_detail(db: Session, message_id: str):
    """Trả về chi tiết 1 tin nhắn cụ thể."""
    try:
        return db.query(Message).filter(Message.id == message_id).first()
    except Exception as e:
        print("❌ [get_message_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🗑️ Xóa tin nhắn (logic)
# ======================================================
def delete_message(db: Session, message_id: str, user_id: str):
    """
    Cho phép người gửi hoặc người nhận xóa tin nhắn của chính mình.
    Có thể xóa vật lý hoặc logic tùy nhu cầu.
    """
    try:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            print("⚠️ [delete_message] Không tìm thấy tin nhắn.")
            return False

        # ✅ Kiểm tra quyền sở hữu
        if msg.sender_id != user_id and msg.receiver_id != user_id:
            print("⚠️ [delete_message] Không có quyền xóa.")
            return False

        # ✅ Nếu có file đính kèm, xóa file vật lý (tùy chọn)
        if msg.attachment_url and Path(msg.attachment_url).exists():
            try:
                os.remove(msg.attachment_url)
            except Exception:
                pass

        db.delete(msg)
        db.commit()
        print(f"🗑️ [delete_message] Đã xóa tin nhắn {message_id}")
        return True

    except Exception as e:
        db.rollback()
        print("❌ [delete_message] Lỗi:", e)
        traceback.print_exc()
        return False
