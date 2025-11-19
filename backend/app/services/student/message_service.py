"""
==========================================================
📘 SERVICE: Student - Message (Tin nhắn nội bộ)
Xử lý logic gửi, nhận và hiển thị tin nhắn cho học viên
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
    """
    Trả về danh sách tin nhắn mà user nhận được.
    Sắp xếp theo thời gian mới nhất.
    """
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
    """
    Trả về danh sách tin nhắn mà user đã gửi.
    """
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
    Nếu có file đính kèm sẽ upload và lưu metadata.
    """

    try:
        # Không cho gửi tin nhắn rỗng
        if not content and not (attachment and attachment.filename):
            print("⚠️ [send_message] Tin nhắn rỗng, không gửi.")
            return None

        uploads_dir = Path("uploads/messages")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        attachment_url = None
        attachment_name = None
        attachment_size = None

        # ==============================================
        # 📎 Upload file đính kèm (nếu có)
        # ==============================================
        if attachment and attachment.filename:
            safe_filename = attachment.filename.replace(" ", "_")

            filename = f"{uuid.uuid4().hex}_{safe_filename}"
            file_path = uploads_dir / filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            attachment_url = f"/uploads/messages/{filename}"
            attachment_name = safe_filename
            attachment_size = os.path.getsize(file_path)

            print(f"📎 [send_message] Saved file: {file_path}")

        # ==============================================
        # 📨 Tạo message record
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
    """Lấy thông tin chi tiết một tin nhắn."""
    try:
        return db.query(Message).filter(Message.id == message_id).first()
    except Exception as e:
        print("❌ [get_message_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🗑️ Xóa tin nhắn
# ======================================================
def delete_message(db: Session, message_id: str, user_id: str):
    """
    Xóa tin nhắn.
    ✔ Chỉ người gửi hoặc người nhận được phép xóa.
    ✔ Nếu có file đính kèm thì xóa luôn file vật lý.
    """
    try:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            print("⚠️ [delete_message] Không tìm thấy tin nhắn.")
            return False

        # Kiểm tra quyền
        if msg.sender_id != user_id and msg.receiver_id != user_id:
            print("⚠️ [delete_message] Không có quyền xóa.")
            return False

        # Xóa file đính kèm nếu có
        if msg.attachment_url:
            physical_path = Path(msg.attachment_url.lstrip("/"))

            if physical_path.exists():
                try:
                    os.remove(physical_path)
                    print(f"🗑️ [delete_message] Đã xóa file: {physical_path}")
                except Exception as e:
                    print("⚠️ Không thể xóa file đính kèm:", e)

        # Xóa message trong DB
        db.delete(msg)
        db.commit()

        print(f"🗑️ [delete_message] Đã xóa tin nhắn {message_id}")
        return True

    except Exception as e:
        db.rollback()
        print("❌ [delete_message] Lỗi:", e)
        traceback.print_exc()
        return False
