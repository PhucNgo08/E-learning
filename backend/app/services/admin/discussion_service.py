from datetime import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.discussion import Discussion


def get_all_discussions(db: Session, course_id: str = None):
    query = db.query(Discussion)
    if course_id:
        query = query.filter(Discussion.course_id == course_id)
    return query.order_by(Discussion.created_at.desc()).all()


def create_discussion(
    db: Session,
    course_id: str,
    user_id: str,
    content: str,
    parent_id: str = None,
):
    if not content or not content.strip():
        raise ValueError("Nội dung thảo luận không được để trống.")

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

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi tạo thảo luận: {str(e)}") from e


def _collect_child_ids(db: Session, discussion_id: str):
    child_ids = []
    direct_children = (
        db.query(Discussion.id)
        .filter(Discussion.parent_id == discussion_id)
        .all()
    )

    for row in direct_children:
        child_id = row[0]
        child_ids.append(child_id)
        child_ids.extend(_collect_child_ids(db, child_id))

    return child_ids


def delete_discussion(db: Session, discussion_id: str):
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return None

    try:
        child_ids = _collect_child_ids(db, discussion_id)

        if child_ids:
            (
                db.query(Discussion)
                .filter(Discussion.id.in_(child_ids))
                .delete(synchronize_session=False)
            )

        db.delete(discussion)
        db.commit()
        return discussion

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa thảo luận: {str(e)}") from e


def get_discussion_by_id(db: Session, discussion_id: str):
    return db.query(Discussion).filter(Discussion.id == discussion_id).first()


def count_discussions_by_course(db: Session, course_id: str):
    return (
        db.query(func.count(Discussion.id))
        .filter(Discussion.course_id == course_id)
        .scalar()
        or 0
    )


def delete_by_course(db: Session, course_id: str):
    try:
        count = (
            db.query(Discussion)
            .filter(Discussion.course_id == course_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return count
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa thảo luận theo khóa học: {str(e)}") from e