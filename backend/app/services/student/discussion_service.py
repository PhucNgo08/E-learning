"""
==========================================================
📗 Service: Discussion (Thảo luận học viên)
Xử lý diễn đàn trao đổi và phản hồi trong khóa học
==========================================================
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from sqlalchemy import or_

from app.models.discussion import Discussion
from app.models.user import User

# ==========================================================
# 🧩 Helper: Gắn thông tin tác giả và khóa học
# ==========================================================
def attach_author_and_course(db: Session, discussion: Discussion):
    from app.models.course import Course
    discussion.author = db.query(User).filter(User.id == discussion.user_id).first()
    discussion.course = db.query(Course).filter(Course.id == discussion.course_id).first()
    return discussion


# ==========================================================
# 🔹 Lấy tất cả bài thảo luận của mọi khóa học
# ==========================================================
def get_all_discussions_all_courses(db: Session):
    """Lấy toàn bộ bài thảo luận (mọi khóa học, sắp xếp theo thời gian mới nhất)."""
    discussions = (
        db.query(Discussion)
        .filter(Discussion.parent_id == None)
        .order_by(Discussion.created_at.desc())
        .all()
    )
    for d in discussions:
        attach_author_and_course(db, d)
    return discussions


# ==========================================================
# 🔹 Lấy danh sách tất cả bài thảo luận trong 1 khóa học
# ==========================================================
def get_all_discussions(db: Session, course_id: str):
    """Lấy danh sách bài thảo luận thuộc một khóa học cụ thể."""
    discussions = (
        db.query(Discussion)
        .filter(Discussion.course_id == course_id, Discussion.parent_id == None)
        .order_by(Discussion.created_at.desc())
        .all()
    )
    for d in discussions:
        attach_author_and_course(db, d)
    return discussions


# ==========================================================
# 🔹 Lấy chi tiết bài thảo luận + reply tree
# ==========================================================
def get_discussion_with_replies(db: Session, discussion_id: str):
    """Lấy chi tiết bài thảo luận và phản hồi nhiều cấp (tree)."""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return None, []

    discussion.author = db.query(User).filter(User.id == discussion.user_id).first()

    replies = (
        db.query(Discussion)
        .filter(Discussion.parent_id == discussion_id)
        .order_by(Discussion.created_at.asc())
        .all()
    )
    for r in replies:
        r.author = db.query(User).filter(User.id == r.user_id).first()
        # ✅ Lấy reply cấp con (nếu có)
        r.children = (
            db.query(Discussion)
            .filter(Discussion.parent_id == r.id)
            .order_by(Discussion.created_at.asc())
            .all()
        )
        for c in r.children:
            c.author = db.query(User).filter(User.id == c.user_id).first()

    return discussion, replies


# ==========================================================
# 🔹 Thêm bài thảo luận mới
# ==========================================================
def add_discussion(db: Session, course_id: str, user_id: str, content: str):
    """Sinh viên tạo một bài thảo luận mới trong khóa học."""
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
        print("❌ [add_discussion] Lỗi:", e)
        return None


# ==========================================================
# 🔹 Thêm phản hồi (reply, hỗ trợ nhiều cấp)
# ==========================================================
def add_reply(db: Session, discussion_id: str, user_id: str, content: str, parent_id: str = None):
    """Thêm phản hồi vào bài thảo luận (hỗ trợ reply nhiều cấp)."""
    # Nếu reply vào bài chính => parent_id = discussion_id
    if parent_id is None:
        parent_id = discussion_id

    course_id = (
        db.query(Discussion.course_id)
        .filter(Discussion.id == discussion_id)
        .scalar()
    )
    if not course_id:
        return {"error": "Không thể thêm phản hồi vì bài thảo luận gốc không tồn tại."}

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
# 🔹 Xóa bài thảo luận hoặc phản hồi
# ==========================================================
def delete_discussion(db: Session, discussion_id: str, user_id: str):
    """Cho phép sinh viên xóa bài viết hoặc phản hồi của chính mình."""
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == user_id)
        .first()
    )
    if not discussion:
        return {"error": "Không tìm thấy hoặc không có quyền xóa."}

    try:
        # ✅ Xóa cả reply con
        replies = db.query(Discussion).filter(Discussion.parent_id == discussion_id).all()
        for r in replies:
            db.delete(r)
        db.delete(discussion)
        db.commit()
        return {"success": True, "message": "Đã xóa bài thảo luận và phản hồi liên quan."}
    except Exception as e:
        db.rollback()
        print("❌ [delete_discussion] Lỗi:", e)
        return {"error": "Không thể xóa bài thảo luận."}


# ==========================================================
# 🔹 Like / Dislike bài thảo luận
# ==========================================================
def toggle_like(db: Session, discussion_id: str, user_id: str):
    """
    Toggle like/dislike cho bài thảo luận.
    Bảng cần: discussion_likes(id, discussion_id, user_id, created_at)
    """
    from app.models.discussion_like import DiscussionLike

    existing = (
        db.query(DiscussionLike)
        .filter(DiscussionLike.discussion_id == discussion_id, DiscussionLike.user_id == user_id)
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"unliked": True}

    like = DiscussionLike(
        id=str(uuid.uuid4()),
        discussion_id=discussion_id,
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(like)
    db.commit()
    return {"liked": True}


# ==========================================================
# 🔹 Tìm kiếm bài thảo luận theo từ khóa
# ==========================================================
def search_discussions(db: Session, keyword: str):
    """Tìm kiếm bài thảo luận theo nội dung hoặc tên người đăng."""
    if not keyword:
        return get_all_discussions_all_courses(db)

    keyword = f"%{keyword.strip()}%"
    discussions = (
        db.query(Discussion)
        .join(User, User.id == Discussion.user_id)
        .filter(
            Discussion.parent_id == None,
            or_(
                Discussion.content.like(keyword),
                User.full_name.like(keyword),
            ),
        )
        .order_by(Discussion.created_at.desc())
        .all()
    )
    for d in discussions:
        attach_author_and_course(db, d)
    return discussions


# ==========================================================
# 🔹 Cập nhật bài thảo luận
# ==========================================================
def update_discussion(db: Session, discussion_id: str, user_id: str, new_content: str):
    """Cho phép người dùng chỉnh sửa nội dung bài thảo luận của mình."""
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == user_id)
        .first()
    )
    if not discussion:
        return {"error": "Không tìm thấy hoặc không có quyền chỉnh sửa."}

    try:
        discussion.content = new_content.strip()
        discussion.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(discussion)
        return discussion
    except Exception as e:
        db.rollback()
        print("❌ [update_discussion] Lỗi:", e)
        return None


# ==========================================================
# 🔹 Lấy danh sách phản hồi con theo discussion_id
# ==========================================================
def get_replies(db: Session, discussion_id: str):
    """Lấy danh sách phản hồi con theo discussion_id."""
    replies = (
        db.query(Discussion)
        .filter(Discussion.parent_id == discussion_id)
        .order_by(Discussion.created_at.asc())
        .all()
    )
    for r in replies:
        r.author = db.query(User).filter(User.id == r.user_id).first()
    return replies
