from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.course_review import CourseReview


def get_review_statistics(db: Session, course_id: str | None = None):
    """
    Thống kê đánh giá khóa học.
    - Nếu có course_id: thống kê theo 1 khóa học
    - Nếu không có course_id: thống kê toàn hệ thống
    """
    query = db.query(CourseReview)

    if course_id:
        query = query.filter(CourseReview.course_id == course_id)

    avg_rating = query.with_entities(func.avg(CourseReview.overall_rating)).scalar() or 0
    total_reviews = query.with_entities(func.count(CourseReview.id)).scalar() or 0

    stars = []
    for s in range(5, 0, -1):
        star_query = db.query(func.count(CourseReview.id))
        if course_id:
            star_query = star_query.filter(CourseReview.course_id == course_id)

        count = star_query.filter(
            func.round(CourseReview.overall_rating) == s
        ).scalar() or 0

        stars.append(count)

    return {
        "avg_rating": round(float(avg_rating), 2),
        "star_distribution": stars,
        "total_reviews": int(total_reviews),
    }