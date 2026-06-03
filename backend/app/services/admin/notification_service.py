"""
==========================================================
📢 SERVICE: Notification Management
Quản lý thông báo hệ thống
- Lấy danh sách thông báo
- Tạo thông báo cho 1 người
- Tạo thông báo cho nhiều người
- Gửi thông báo theo khóa học
- Gửi thông báo cho tất cả người dùng
- Đánh dấu đã đọc
- Xóa thông báo
==========================================================
"""
from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment


ACTIVE_ENROLLMENT_STATUSES = ("approved", "active", "completed")


# ======================================================
# GET
# ======================================================
def get_all_notifications(db: Session) -> list[Notification]:
    return (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_notification_by_id(db: Session, noti_id: str) -> Notification | None:
    if not noti_id:
        return None

    return (
        db.query(Notification)
        .filter(Notification.id == noti_id)
        .first()
    )


def get_course_student_ids(db: Session, course_id: str) -> list[str]:
    """
    Lấy danh sách sinh viên đang học trong một khóa học.
    Chỉ lấy các trạng thái ghi danh hợp lệ.
    """
    if not course_id:
        return []

    rows = (
        db.query(CourseEnrollment.user_id)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_ENROLLMENT_STATUSES),
        )
        .all()
    )

    return list(dict.fromkeys([row.user_id for row in rows if row.user_id]))


def get_all_user_ids(db: Session) -> list[str]:
    rows = db.query(User.id).all()
    return list(dict.fromkeys([row.id for row in rows if row.id]))


# ======================================================
# CREATE
# ======================================================
def create_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> Notification:
    """
    Tạo 1 thông báo cho 1 người dùng.
    Giữ hàm này để các chức năng cũ trong hệ thống không bị lỗi.
    """
    title = (title or "").strip()
    message = (message or "").strip()
    notification_type = (notification_type or "system").strip() or "system"
    link_url = (link_url or "").strip() or None

    if not user_id:
        raise ValueError("Thiếu user_id khi tạo thông báo.")

    if not title:
        raise ValueError("Tiêu đề thông báo không được để trống.")

    if not message:
        raise ValueError("Nội dung thông báo không được để trống.")

    new_noti = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
        created_at=datetime.utcnow(),
        is_read=False,
        read_at=None,
    )

    try:
        db.add(new_noti)
        db.commit()
        db.refresh(new_noti)
        return new_noti

    except SQLAlchemyError:
        db.rollback()
        raise


def create_notifications_for_users(
    db: Session,
    user_ids: list[str],
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> int:
    """
    Tạo thông báo cho nhiều người dùng.
    Dùng cho:
    - Chọn từng người nhận
    - Gửi theo khóa học
    - Gửi tất cả người dùng

    Trả về số thông báo đã tạo.
    """
    title = (title or "").strip()
    message = (message or "").strip()
    notification_type = (notification_type or "system").strip() or "system"
    link_url = (link_url or "").strip() or None

    unique_user_ids = list(dict.fromkeys([uid for uid in user_ids if uid]))

    if not unique_user_ids:
        raise ValueError("Danh sách người nhận rỗng.")

    if not title:
        raise ValueError("Tiêu đề thông báo không được để trống.")

    if not message:
        raise ValueError("Nội dung thông báo không được để trống.")

    try:
        for uid in unique_user_ids:
            db.add(
                Notification(
                    id=str(uuid.uuid4()),
                    user_id=uid,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    link_url=link_url,
                    created_at=datetime.utcnow(),
                    is_read=False,
                    read_at=None,
                )
            )

        db.commit()
        return len(unique_user_ids)

    except SQLAlchemyError:
        db.rollback()
        raise


def create_notifications_for_course(
    db: Session,
    course_id: str,
    title: str,
    message: str,
    notification_type: str = "course",
    link_url: str | None = None,
) -> int:
    """
    Gửi thông báo cho sinh viên trong một khóa học.
    """
    if not course_id:
        raise ValueError("Thiếu course_id khi gửi thông báo theo khóa học.")

    course = (
        db.query(Course)
        .filter(Course.id == course_id)
        .first()
    )

    if not course:
        raise ValueError("Khóa học không tồn tại.")

    student_ids = get_course_student_ids(db, course_id)

    if not student_ids:
        raise ValueError("Khóa học này chưa có sinh viên đang học.")

    return create_notifications_for_users(
        db=db,
        user_ids=student_ids,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
    )


def create_notifications_for_all_users(
    db: Session,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str | None = None,
) -> int:
    """
    Gửi thông báo cho tất cả người dùng trong hệ thống.
    """
    user_ids = get_all_user_ids(db)

    if not user_ids:
        raise ValueError("Không có người dùng nào trong hệ thống.")

    return create_notifications_for_users(
        db=db,
        user_ids=user_ids,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url,
    )


# ======================================================
# UPDATE
# ======================================================
def mark_as_read(db: Session, noti_id: str) -> bool:
    """
    Đánh dấu một thông báo là đã đọc.
    """
    noti = get_notification_by_id(db, noti_id)

    if not noti:
        return False

    if not noti.is_read:
        try:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()

        except SQLAlchemyError:
            db.rollback()
            raise

    return True


def mark_all_as_read_by_user(db: Session, user_id: str) -> int:
    """
    Đánh dấu tất cả thông báo của một người dùng là đã đọc.
    Trả về số dòng đã cập nhật.
    """
    if not user_id:
        return 0

    try:
        updated_count = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .update(
                {
                    Notification.is_read: True,
                    Notification.read_at: datetime.utcnow(),
                },
                synchronize_session=False,
            )
        )

        db.commit()
        return updated_count

    except SQLAlchemyError:
        db.rollback()
        raise


# ======================================================
# DELETE
# ======================================================
def delete_notification(db: Session, noti_id: str) -> Notification | None:
    """
    Xóa một thông báo theo id.
    """
    noti = get_notification_by_id(db, noti_id)

    if not noti:
        return None

    try:
        db.delete(noti)
        db.commit()
        return noti

    except SQLAlchemyError:
        db.rollback()
        raise


def delete_notifications_by_user(db: Session, user_id: str) -> int:
    """
    Xóa toàn bộ thông báo của một người dùng.
    Dùng khi cần dọn dữ liệu.
    """
    if not user_id:
        return 0

    try:
        deleted_count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .delete(synchronize_session=False)
        )

        db.commit()
        return deleted_count

    except SQLAlchemyError:
        db.rollback()
        raise