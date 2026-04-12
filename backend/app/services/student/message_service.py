
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import traceback
import uuid

from sqlalchemy.orm import Session

from app.config.paths import UPLOAD_MESSAGES, build_upload_url, resolve_upload_path_from_url
from app.models.message import Message
from app.models.user import User
from app.services.student.notification_service import create_notification

UPLOAD_DIR = UPLOAD_MESSAGES
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_inbox_messages(db: Session, user_id: str):
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


def get_sent_messages(db: Session, user_id: str):
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


def _save_attachment(attachment) -> tuple[str | None, str | None, int | None]:
    if not attachment or not getattr(attachment, "filename", None):
        return None, None, None

    safe_name = Path(attachment.filename).name.replace(" ", "_")
    filename = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(attachment.file, buffer)

    attachment_url = build_upload_url("messages", filename)
    attachment_name = safe_name
    attachment_size = os.path.getsize(file_path)
    return attachment_url, attachment_name, attachment_size


def send_message(db: Session, sender_id: str, receiver_id: str, content: str, attachment=None):
    try:
        clean_content = (content or "").strip()

        if sender_id == receiver_id:
            return None

        if not clean_content and not (attachment and attachment.filename):
            return None

        attachment_url, attachment_name, attachment_size = _save_attachment(attachment)

        msg = Message(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=clean_content,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            attachment_size=attachment_size,
            sent_at=datetime.utcnow(),
            is_read=0,
            read_at=None,
        )

        db.add(msg)
        db.commit()
        db.refresh(msg)

        receiver = db.query(User).filter(User.id == receiver_id).first()
        if receiver:
            receiver_role = getattr(receiver, "role", "") or "student"
            prefix = "/student" if receiver_role == "student" else "/teacher"
            preview = clean_content[:80] if clean_content else "(Tệp đính kèm)"

            create_notification(
                db=db,
                user_id=receiver_id,
                title="📩 Tin nhắn mới",
                message=f"Bạn có tin nhắn mới: '{preview}'",
                notification_type="message",
                link_url=f"{prefix}/message/view/{msg.id}",
            )

        return msg

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def get_message_detail(db: Session, message_id: str):
    try:
        return db.query(Message).filter(Message.id == message_id).first()
    except Exception:
        traceback.print_exc()
        return None


def mark_as_read(db: Session, message_id: str, viewer_id: str):
    try:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            return None

        if msg.receiver_id != viewer_id:
            return msg

        if int(getattr(msg, "is_read", 0) or 0) != 1:
            msg.is_read = 1
            msg.read_at = datetime.utcnow()
            db.commit()
            db.refresh(msg)

        return msg

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def resolve_attachment_path(msg: Message) -> Path | None:
    try:
        file_path = resolve_upload_path_from_url((msg.attachment_url or "").strip())
        if file_path and file_path.exists() and file_path.is_file():
            return file_path.resolve()
        return None
    except Exception:
        traceback.print_exc()
        return None


def delete_message(db: Session, message_id: str, user_id: str):
    try:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            return False

        if msg.sender_id != user_id and msg.receiver_id != user_id:
            return False

        file_path = resolve_attachment_path(msg)
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass

        db.delete(msg)
        db.commit()
        return True

    except Exception:
        db.rollback()
        traceback.print_exc()
        return False
