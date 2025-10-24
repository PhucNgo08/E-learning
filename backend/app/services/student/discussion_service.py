"""
📗 Service: Discussion (Thảo luận)
Xử lý diễn đàn trao đổi của học viên
"""

from sqlalchemy.orm import Session
from app.models.discussion import Discussion
from datetime import datetime
import uuid

def get_all_discussions(db: Session, course_id: str):
    """Lấy danh sách thảo luận trong khóa học"""
    return db.query(Discussion).filter(Discussion.course_id == course_id).order_by(Discussion.created_at.desc()).all()

def add_discussion(db: Session, course_id: str, user_id: str, content: str):
    """Tạo bài thảo luận mới"""
    discussion = Discussion(
        id=str(uuid.uuid4()),
        course_id=course_id,
        user_id=user_id,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return discussion
