from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.course_enrollment import CourseEnrollment

ACTIVE_COURSE_ENROLLMENT_STATUSES = frozenset({"approved", "active", "completed"})
PURCHASE_ENROLLMENT_SOURCES = frozenset({"purchase", "wallet", "order", "paid", "vnpay", "card"})


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower()


def get_accessible_course_ids(db: Session, user_id: str | None) -> set[str]:
    """
    Trả về tập course_id mà user đang có quyền học.
    Nguồn sự thật duy nhất: course_enrollments
    """
    if not user_id:
        return set()

    rows = (
        db.query(CourseEnrollment.course_id)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_COURSE_ENROLLMENT_STATUSES),
        )
        .all()
    )

    return {row[0] for row in rows if row and row[0]}


def has_course_access(db: Session, user_id: str | None, course_id: str | None) -> bool:
    """
    Kiểm tra user có quyền truy cập course hay không.
    """
    if not user_id or not course_id:
        return False

    return (
        db.query(CourseEnrollment.id)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_COURSE_ENROLLMENT_STATUSES),
        )
        .first()
        is not None
    )


def get_active_course_enrollment(
    db: Session,
    user_id: str | None,
    course_id: str | None,
) -> CourseEnrollment | None:
    """
    Lấy enrollment đang có hiệu lực của user trong course.
    """
    if not user_id or not course_id:
        return None

    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(ACTIVE_COURSE_ENROLLMENT_STATUSES),
        )
        .first()
    )


def is_purchase_enrollment(enrollment: CourseEnrollment | None) -> bool:
    if not enrollment:
        return False
    source = _normalize(getattr(enrollment, "enrollment_source", None))
    return source in PURCHASE_ENROLLMENT_SOURCES


def get_course_access_flags(db: Session, user_id: str | None, course_id: str | None) -> dict[str, bool]:
    enrollment = get_active_course_enrollment(db, user_id, course_id)
    if not enrollment:
        return {
            "can_access": False,
            "purchased": False,
            "enrolled": False,
        }

    return {
        "can_access": True,
        "purchased": is_purchase_enrollment(enrollment),
        "enrolled": True,
    }