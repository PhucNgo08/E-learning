"""
📙 Service: Review (Đánh giá khóa học)
"""

from sqlalchemy.orm import Session
from app.models.course_review import CourseReview
from datetime import datetime
import uuid

def get_reviews_by_course(db: Session, course_id: str):
    """Lấy danh sách đánh giá"""
    return db.query(CourseReview).filter(CourseReview.course_id == course_id).order_by(CourseReview.created_at.desc()).all()

def submit_review(db: Session, user_id: str, course_id: str, rating: int, comment: str):
    """Thêm đánh giá mới"""
    review = CourseReview(
        id=str(uuid.uuid4()),
        user_id=user_id,
        course_id=course_id,
        rating_content=rating,
        comment=comment,
        created_at=datetime.utcnow()
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
