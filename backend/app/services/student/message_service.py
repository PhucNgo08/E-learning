"""
📘 Service: Message (Tin nhắn nội bộ)
"""

from sqlalchemy.orm import Session
from app.models.message import Message
from datetime import datetime
import uuid

def get_messages_for_user(db: Session, user_id: str):
    """Lấy danh sách tin nhắn đến và đi"""
    return db.query(Message).filter((Message.sender_id == user_id) | (Message.receiver_id == user_id)).order_by(Message.sent_at.desc()).all()

def send_message(db: Session, sender_id: str, receiver_id: str, content: str):
    """Gửi tin nhắn"""
    msg = Message(
        id=str(uuid.uuid4()),
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        sent_at=datetime.utcnow()
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
