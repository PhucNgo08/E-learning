"""
==========================================================
💬 SERVICE: Discussion Management (v2.1)
Xử lý CRUD cho bảng discussions + logging + an toàn
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.discussion import Discussion
from datetime import datetime
import uuid
import traceback


# ==========================================================
# 📋 1️⃣ Lấy tất cả thảo luận
# ==========================================================
def get_all_discussions(db: Session, course_id: str = None):
    """
    Lấy danh sách tất cả thảo luận (có thể lọc theo khóa học)
    """
    query = db.query(Discussion)
    if course_id:
        query = query.filter(Discussion.course_id == course_id)
    return query.order_by(Discussion.created_at.desc()).all()


# ==========================================================
# ➕ 2️⃣ Tạo mới thảo luận
# ==========================================================
def create_discussion(
    db: Session,
    course_id: str,
    user_id: str,
    content: str,
    parent_id: str = None
):
    """
    Tạo thảo luận hoặc trả lời (nếu có parent_id)
    """
    try:
        discussion = Discussion(
            id=str(uuid.uuid4()),
            course_id=course_id,
            user_id=user_id,
            content=content.strip(),
            parent_id=parent_id,
            created_at=datetime.utcnow(),
        )
        db.add(discussion)
        db.commit()
        db.refresh(discussion)
        return discussion
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi tạo discussion: {e}")
        traceback.print_exc()
        return None


# ==========================================================
# 🗑️ 3️⃣ Xóa thảo luận
# ==========================================================
def delete_discussion(db: Session, discussion_id: str):
    """
    Xóa thảo luận (và các câu trả lời con nếu có)
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return None

    # Xóa reply con (nếu có)
    replies = db.query(Discussion).filter(Discussion.parent_id == discussion_id).all()
    for r in replies:
        db.delete(r)

    db.delete(discussion)
    db.commit()
    return discussion


# ==========================================================
# 🔍 4️⃣ Lấy chi tiết thảo luận
# ==========================================================
def get_discussion_by_id(db: Session, discussion_id: str):
    """
    Lấy chi tiết 1 thảo luận
    """
    return db.query(Discussion).filter(Discussion.id == discussion_id).first()


# ==========================================================
# 💬 5️⃣ Lấy số lượng bình luận theo khóa học
# ==========================================================
def count_discussions_by_course(db: Session, course_id: str):
    """
    Đếm tổng số thảo luận trong khóa học (bao gồm cả reply)
    """
    return db.query(func.count(Discussion.id)).filter(Discussion.course_id == course_id).scalar() or 0


# ==========================================================
# 🧹 6️⃣ Xóa toàn bộ thảo luận của 1 khóa học (Admin)
# ==========================================================
def delete_by_course(db: Session, course_id: str):
    """
    Xóa toàn bộ discussion thuộc khóa học (cho admin)
    """
    try:
        count = db.query(Discussion).filter(Discussion.course_id == course_id).delete()
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi xóa thảo luận theo khóa học: {e}")
        traceback.print_exc()
        return 0
