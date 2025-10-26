"""
==========================================================
📗 Service: Discussion (Thảo luận học viên)
Xử lý diễn đàn trao đổi và phản hồi trong khóa học
==========================================================
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.models.discussion import Discussion
from app.models.user import User


# ==========================================================
# 🔹 Lấy tất cả bài thảo luận của mọi khóa học
# ==========================================================
def get_all_discussions_all_courses(db: Session):
    """
    Lấy toàn bộ bài thảo luận (mọi khóa học, sắp xếp theo thời gian mới nhất).
    Dữ liệu trả về có thêm thông tin người đăng và tên khóa học.
    """
    from app.models.course import Course  # tránh vòng lặp import

    discussions = (
        db.query(Discussion)
        .filter(Discussion.parent_id == None)  # chỉ lấy bài gốc, không lấy reply
        .order_by(Discussion.created_at.desc())
        .all()
    )

    for d in discussions:
        d.author = db.query(User).filter(User.id == d.user_id).first()
        d.course = db.query(Course).filter(Course.id == d.course_id).first()

    return discussions


# ==========================================================
# 🔹 Lấy danh sách tất cả bài thảo luận trong 1 khóa học
# ==========================================================
def get_all_discussions(db: Session, course_id: str):
    """
    Lấy danh sách bài thảo luận thuộc một khóa học cụ thể.
    """
    from app.models.course import Course

    discussions = (
        db.query(Discussion)
        .filter(Discussion.course_id == course_id, Discussion.parent_id == None)
        .order_by(Discussion.created_at.desc())
        .all()
    )

    for d in discussions:
        d.author = db.query(User).filter(User.id == d.user_id).first()
        d.course = db.query(Course).filter(Course.id == d.course_id).first()

    return discussions


# ==========================================================
# 🔹 Lấy chi tiết 1 bài thảo luận (kèm phản hồi)
# ==========================================================
def get_discussion_detail(db: Session, discussion_id: str):
    """
    Lấy chi tiết một bài thảo luận (bao gồm người đăng và các phản hồi).
    """
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id)
        .first()
    )

    if not discussion:
        return None

    # Gắn thông tin người đăng
    discussion.author = db.query(User).filter(User.id == discussion.user_id).first()

    # ✅ Lấy các phản hồi con (theo parent_id)
    discussion.replies = (
        db.query(Discussion)
        .filter(Discussion.parent_id == discussion_id)
        .order_by(Discussion.created_at.asc())
        .all()
    )

    for r in discussion.replies:
        r.author = db.query(User).filter(User.id == r.user_id).first()

    return discussion


# ==========================================================
# 🔹 Thêm bài thảo luận mới
# ==========================================================
def add_discussion(db: Session, course_id: str, user_id: str, content: str):
    """
    Sinh viên tạo một bài thảo luận mới trong khóa học.
    """
    discussion = Discussion(
        id=str(uuid.uuid4()),
        course_id=course_id,
        user_id=user_id,
        content=content.strip(),
        created_at=datetime.utcnow()
    )

    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return discussion


# ==========================================================
# 🔹 Thêm phản hồi (reply) vào bài thảo luận
# ==========================================================
def add_reply(db: Session, discussion_id: str, user_id: str, content: str):
    """
    Thêm phản hồi (comment) vào bài thảo luận, 
    bản chất là thêm một Discussion có parent_id = discussion_id.
    """
    # Lấy course_id từ bài gốc
    course_id = (
        db.query(Discussion.course_id)
        .filter(Discussion.id == discussion_id)
        .scalar()
    )

    reply = Discussion(
        id=str(uuid.uuid4()),
        course_id=course_id,
        user_id=user_id,
        content=content.strip(),
        parent_id=discussion_id,
        created_at=datetime.utcnow()
    )

    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


# ==========================================================
# 🔹 Xóa bài thảo luận
# ==========================================================
def delete_discussion(db: Session, discussion_id: str, user_id: str):
    """
    Cho phép sinh viên xóa bài viết của chính mình.
    Khi xóa, các phản hồi con cũng bị xóa theo cascade.
    """
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == user_id)
        .first()
    )

    if not discussion:
        return {"error": "Không tìm thấy hoặc không có quyền xóa."}

    db.delete(discussion)
    db.commit()
    return {"success": True, "message": "Đã xóa bài thảo luận."}


# ==========================================================
# 🔹 Cập nhật bài thảo luận
# ==========================================================
def update_discussion(db: Session, discussion_id: str, user_id: str, new_content: str):
    """
    Cho phép người dùng chỉnh sửa nội dung bài thảo luận của mình.
    """
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == user_id)
        .first()
    )

    if not discussion:
        return {"error": "Không tìm thấy hoặc không có quyền chỉnh sửa."}

    discussion.content = new_content.strip()
    discussion.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(discussion)
    return discussion
