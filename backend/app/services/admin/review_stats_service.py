from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.course_review import CourseReview

def get_review_statistics(db: Session, course_id: str):
    """Thống kê điểm đánh giá khóa học"""
    avg_rating = db.query(func.avg(CourseReview.overall_rating)).filter(CourseReview.course_id == course_id).scalar() or 0
    stars = []
    for s in range(5, 0, -1):
        count = db.query(func.count(CourseReview.id)).filter(
            CourseReview.course_id == course_id,
            func.round(CourseReview.overall_rating) == s
        ).scalar()
        stars.append(count)
    return {"avg_rating": round(avg_rating, 2), "star_distribution": stars}
