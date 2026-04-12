"""
==========================================================
📘 SERVICE: Teacher - Message (Tin nhắn nội bộ)
Xử lý logic gửi, nhận và hiển thị tin nhắn
==========================================================
"""

from datetime import datetime
from pathlib import Path
import shutil
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.config.paths import UPLOAD_MESSAGES, build_upload_url
from app.models.message import Message


UPLOAD_DIR = UPLOAD_MESSAGES
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_inbox_messages(db: Session, user_id: str):
    """Lấy tin nhắn đến (receiver_id = user_id)"""
    try:
        return (
            db.query(Message)
            .options(joinedload(Message.sender), joinedload(Message.receiver))
            .filter(Message.receiver_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [Teacher:get_inbox_messages] Lỗi:", e)
        return []


def get_sent_messages(db: Session, user_id: str):
    """Lấy tin nhắn đã gửi (sender_id = user_id)"""
    try:
        return (
            db.query(Message)
            .options(joinedload(Message.sender), joinedload(Message.receiver))
            .filter(Message.sender_id == user_id)
            .order_by(Message.sent_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [Teacher:get_sent_messages] Lỗi:", e)
        return []


def get_message_detail_for_user(db: Session, message_id: str, user_id: str):
    """Chỉ cho xem nếu user là người gửi hoặc người nhận"""
    try:
        return (
            db.query(Message)
            .options(joinedload(Message.sender), joinedload(Message.receiver))
            .filter(
                Message.id == message_id,
                ((Message.sender_id == user_id) | (Message.receiver_id == user_id)),
            )
            .first()
        )
    except Exception as e:
        print("❌ [Teacher:get_message_detail_for_user] Lỗi:", e)
        return None


def send_message(db: Session, sender_id: str, receiver_id: str, content: str, attachment=None):
    """
    Gửi tin nhắn từ giáo viên → người nhận.
    Nếu có file đính kèm, lưu file và ghi lại đường dẫn.
    """
    content = _clean_text(content)

    if not sender_id or not receiver_id:
        return {"error": "Thiếu thông tin người gửi hoặc người nhận."}

    if not content and not (attachment and getattr(attachment, "filename", None)):
        return {"error": "Nội dung tin nhắn hoặc tệp đính kèm không được để trống."}

    if sender_id == receiver_id:
        return {"error": "Không thể tự gửi tin nhắn cho chính mình."}

    try:
        attachment_url = None
        attachment_name = None
        attachment_size = None

        if attachment and getattr(attachment, "filename", None):
            original_name = Path(attachment.filename).name
            filename = f"{uuid.uuid4().hex}_{original_name.replace(' ', '_')}"
            file_path = UPLOAD_DIR / filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(attachment.file, buffer)

            attachment_url = build_upload_url("messages", filename)
            attachment_name = original_name
            attachment_size = file_path.stat().st_size

        msg = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content or "",
            sent_at=datetime.utcnow(),
            read_at=None,
            is_read=0,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_size=attachment_size,
        )

        db.add(msg)
        db.commit()
        db.refresh(msg)

        print(f"✅ [Teacher:send_message] {sender_id} ➜ {receiver_id}")
        return {"success": True, "message": msg}

    except SQLAlchemyError as e:
        db.rollback()
        print("❌ [Teacher:send_message] Lỗi DB:", e)
        return {"error": str(e)}
    except Exception as e:
        db.rollback()
        print("❌ [Teacher:send_message] Lỗi:", e)
        return {"error": str(e)}
