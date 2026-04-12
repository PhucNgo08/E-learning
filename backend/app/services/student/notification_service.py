"""
==========================================================
📢 Student Notification Service (SYNC FIXED)
==========================================================
"""

from datetime import datetime
import traceback
import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "system",
    link_url: str = None
):
    try:
        noti = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=(title or "").strip(),
            message=(message or "").strip(),
            notification_type=notification_type or "system",
            link_url=link_url,
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(noti)
        db.commit()
        db.refresh(noti)
        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def get_user_notifications(db: Session, user_id: str):
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
    except Exception:
        traceback.print_exc()
        return []


def get_latest_notifications(db: Session, user_id: str, limit: int = 10):
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception:
        traceback.print_exc()
        return []


def get_notifications_by_type(db: Session, user_id: str, n_type: str):
    try:
        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.notification_type == n_type,
            )
            .order_by(Notification.created_at.desc())
            .all()
        )
    except Exception:
        traceback.print_exc()
        return []


def get_notification_for_user(db: Session, notification_id: str, user_id: str):
    try:
        return (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )
    except Exception:
        traceback.print_exc()
        return None


def get_notification_detail(db: Session, notification_id: str, user_id: str):
    try:
        noti = get_notification_for_user(db, notification_id, user_id)
        if not noti:
            return None

        if not noti.is_read:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
            db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def mark_as_read(db: Session, notification_id: str, user_id: str):
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if noti and not noti.is_read:
            noti.is_read = True
            noti.read_at = datetime.utcnow()
            db.commit()
            db.refresh(noti)

        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def toggle_read_status(db: Session, notification_id: str, user_id: str):
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if not noti:
            return None

        if noti.is_read:
            noti.is_read = False
            noti.read_at = None
        else:
            noti.is_read = True
            noti.read_at = datetime.utcnow()

        db.commit()
        db.refresh(noti)
        return noti

    except Exception:
        db.rollback()
        traceback.print_exc()
        return None


def mark_all_as_read(db: Session, user_id: str):
    try:
        count = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
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
        return count

    except Exception:
        db.rollback()
        traceback.print_exc()
        return 0


def count_unread_notifications(db: Session, user_id: str):
    try:
        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .count()
        )
    except Exception:
        traceback.print_exc()
        return 0


def delete_notification(db: Session, notification_id: str, user_id: str):
    try:
        noti = get_notification_for_user(db, notification_id, user_id)

        if not noti:
            return False

        db.delete(noti)
        db.commit()
        return True

    except Exception:
        db.rollback()
        traceback.print_exc()
        return False


def delete_all_notifications(db: Session, user_id: str):
    try:
        count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return count

    except Exception:
        db.rollback()
        traceback.print_exc()
        return 0


def get_notifications_paginated(db: Session, user_id: str, skip: int = 0, limit: int = 20):
    try:
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except Exception:
        traceback.print_exc()
        return []


def get_user_notification_settings(db: Session, user_id: str):
    return {
        "system": True,
        "course": True,
        "assignment": True,
        "quiz": True,
        "message": True,
    }


def update_user_notification_settings(db: Session, user_id: str, new_settings: dict):
    return new_settings