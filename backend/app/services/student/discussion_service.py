"""
==========================================================
📗 Service: Discussion (Thảo luận học viên)
Phiên bản FULL 2025 – Tối ưu hiệu năng – Reply tree nhiều cấp
==========================================================
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from datetime import datetime
import uuid

from app.models.discussion import Discussion
from app.models.user import User
from app.models.user_profile import UserProfile
from backend.app import db

# ==========================================================
# 🧩 Helper: Load dữ liệu JOIN sẵn user, course
# ==========================================================
def preload(discussion: Discussion):
    """Thêm thông tin tác giả vào object (nhanh, không tốn query)."""
    discussion.author = discussion.user
    return discussion


# ==========================================================
# 🔹 Lấy toàn bộ bài thảo luận (mọi khóa học)
# ==========================================================
def get_all_discussions_all_courses(db: Session):
    discussions = (
        db.query(Discussion)
        .options(
            joinedload(Discussion.user),
            joinedload(Discussion.course),
        )
        .filter(Discussion.parent_id == None)
        .order_by(Discussion.created_at.desc())
        .all()
    )
    return [preload(d) for d in discussions]


# ==========================================================
# 🔹 Lấy bài thảo luận của 1 khóa học
# ==========================================================
def get_all_discussions(db: Session, course_id: str):
    discussions = (
        db.query(Discussion)
        .options(
            joinedload(Discussion.user),
            joinedload(Discussion.course),
        )
        .filter(
            Discussion.course_id == course_id,
            Discussion.parent_id == None,
        )
        .order_by(Discussion.created_at.desc())
        .all()
    )
    return [preload(d) for d in discussions]


# ==========================================================
# 🔹 Đệ quy xây dựng cây reply nhiều cấp
# ==========================================================
def build_reply_tree(db: Session, parent_id: str):
    """Tạo reply tree vô hạn cấp độ."""
    children = (
        db.query(Discussion)
        .options(joinedload(Discussion.user))
        .filter(Discussion.parent_id == parent_id)
        .order_by(Discussion.created_at.asc())
        .all()
    )

    for child in children:
        child.author = child.user
        child.reply_tree = build_reply_tree(db, child.id)  # KHÔNG ghi đè `children`

    return children


# ==========================================================
# 🔹 Lấy bài thảo luận + toàn bộ reply tree
# ==========================================================
def get_discussion_with_replies(db: Session, discussion_id: str):
    discussion = (
        db.query(Discussion)
        .options(
            joinedload(Discussion.user),
            joinedload(Discussion.course),
        )
        .filter(Discussion.id == discussion_id)
        .first()
    )

    if not discussion:
        return None, []

    discussion.author = discussion.user
    replies = build_reply_tree(db, discussion_id)

    return discussion, replies


# ==========================================================
# 🔹 Thêm bài thảo luận mới
# ==========================================================
def add_discussion(db: Session, course_id: str, user_id: str, content: str):
    try:
        discussion = Discussion(
            id=str(uuid.uuid4()),
            course_id=course_id,
            user_id=user_id,
            content=content.strip(),
            created_at=datetime.utcnow(),
        )
        db.add(discussion)
        db.commit()
        db.refresh(discussion)
        return discussion

    except Exception as e:
        db.rollback()
        print("❌ [add_discussion] Error:", e)
        return None


# ==========================================================
# 🔹 Thêm reply (nhiều cấp)
# ==========================================================
def add_reply(db: Session, discussion_id: str, user_id: str, content: str, parent_id: str = None):
    # nếu parent_id rỗng → reply vào bài gốc
    if parent_id is None:
        parent_id = discussion_id

    course_id = (
        db.query(Discussion.course_id)
        .filter(Discussion.id == discussion_id)
        .scalar()
    )

    if not course_id:
        return {"error": "Không tìm thấy bài thảo luận gốc."}

    reply = Discussion(
        id=str(uuid.uuid4()),
        course_id=course_id,
        user_id=user_id,
        content=content.strip(),
        parent_id=parent_id,
        created_at=datetime.utcnow(),
    )

    db.add(reply)
    db.commit()
    db.refresh(reply)

    return reply


# ==========================================================
# 🔹 Xóa đệ quy toàn bộ reply tree
# ==========================================================
def delete_tree(db: Session, node: Discussion):
    children = db.query(Discussion).filter(Discussion.parent_id == node.id).all()

    for child in children:
        delete_tree(db, child)

    db.delete(node)


def delete_discussion(db: Session, discussion_id: str, user_id: str):
    """Chỉ cho phép xóa bài viết của chính người dùng."""
    discussion = (
        db.query(Discussion)
        .filter(
            Discussion.id == discussion_id,
            Discussion.user_id == user_id,
        )
        .first()
    )

    if not discussion:
        return {"error": "Không tìm thấy bài thảo luận hoặc bạn không có quyền xóa."}

    try:
        delete_tree(db, discussion)
        db.commit()
        return {"success": True}

    except Exception as e:
        db.rollback()
        print("❌ [delete_discussion] Error:", e)
        return {"error": "Xóa thất bại."}


# ==========================================================
# 🔹 Like / Unlike
# ==========================================================
def toggle_like(db: Session, discussion_id: str, user_id: str):
    from app.models.discussion_like import DiscussionLike

    existing = (
        db.query(DiscussionLike)
        .filter(
            DiscussionLike.discussion_id == discussion_id,
            DiscussionLike.user_id == user_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return {"unliked": True}

    like = DiscussionLike(
        discussion_id=discussion_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )

    db.add(like)
    db.commit()

    return {"liked": True}


# ==========================================================
# 🔹 Tìm kiếm bài thảo luận
# ==========================================================
def search_discussions(db: Session, keyword: str):
    if not keyword:
        return get_all_discussions_all_courses(db)

    keyword = f"%{keyword.strip()}%"

    discussions = (
        db.query(Discussion)
            .options(
            joinedload(Discussion.user),
            joinedload(Discussion.course),
        )
        .join(User, User.id == Discussion.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(
            Discussion.parent_id.is_(None),
            or_(
                Discussion.content.like(keyword),
                UserProfile.full_name.like(keyword),
            ),
     )
        .order_by(Discussion.created_at.desc())
        .all()
    )

    return [preload(d) for d in discussions]


# ==========================================================
# 🔹 Lấy reply cấp 1 (AJAX load)
# ==========================================================
def get_replies(db: Session, discussion_id: str):
    replies = (
        db.query(Discussion)
        .options(joinedload(Discussion.user))
        .filter(Discussion.parent_id == discussion_id)
        .order_by(Discussion.created_at.asc())
        .all()
    )

    for r in replies:
        r.author = r.user

    return replies
