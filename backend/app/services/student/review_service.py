"""
==========================================================
🎓 SERVICE: Student - Review Service
Xử lý nghiệp vụ đánh giá khóa học:
- Lấy danh sách đánh giá
- Gửi đánh giá mới
- Kiểm tra sinh viên đã đánh giá chưa
==========================================================
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.models.course_review import CourseReview
from app.models.user import User
import uuid
import traceback

# ======================================================
# ⚙️ Hàm tiện ích
# ======================================================
def uuid_str():
    return str(uuid.uuid4())

# ======================================================
# 📋 Lấy danh sách đánh giá theo khóa học
# ======================================================
def get_reviews_by_course(db: Session, course_id: str):
    """Lấy danh sách các đánh giá đã duyệt của một khóa học cụ thể."""
    try:
        reviews = (
            db.query(
                CourseReview.id,
                CourseReview.title,
                CourseReview.comment,
                CourseReview.rating_content,
                CourseReview.rating_teacher,
                CourseReview.rating_support,
                CourseReview.overall_rating,
                CourseReview.created_at,
                User.full_name.label("user_name"),
            )
            .join(User, User.id == CourseReview.user_id)
            .filter(
                CourseReview.course_id == course_id,
                CourseReview.status == "approved",
            )
            .order_by(CourseReview.created_at.desc())
            .all()
        )
        return reviews
    except Exception as e:
        print("❌ [get_reviews_by_course] Lỗi:", e)
        traceback.print_exc()
        return []

# ======================================================
# ⭐ Gửi (thêm) đánh giá mới
# ======================================================
def submit_review(
    db: Session,
    course_id: str,
    user_id: str,
    rating_content: int,
    rating_teacher: int,
    rating_support: int,
    comment: str,
    title: str = None,
    is_anonymous: bool = False,
):
    """Lưu một đánh giá mới cho khóa học."""
    try:
        overall_rating = round(
            (rating_content + rating_teacher + rating_support) / 3, 2
        )

        review = CourseReview(
            id=uuid_str(),
            course_id=course_id,
            user_id=user_id,
            rating_content=rating_content,
            rating_teacher=rating_teacher,
            rating_support=rating_support,
            overall_rating=overall_rating,
            title=title or "Đánh giá của sinh viên",
            comment=comment.strip(),
            is_anonymous=1 if is_anonymous else 0,
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(review)
        db.commit()
        db.refresh(review)
        print(f"✅ [submit_review] user={user_id}, course={course_id}")
        return review

    except Exception as e:
        db.rollback()
        print("❌ [submit_review] Lỗi:", e)
        traceback.print_exc()
        return None

# ======================================================
# 🔍 Kiểm tra sinh viên đã đánh giá chưa
# ======================================================
def has_student_reviewed(db: Session, course_id: str, user_id: str) -> bool:
    """Trả về True nếu sinh viên đã từng đánh giá khóa học này."""
    try:
        exists = (
            db.query(CourseReview)
            .filter(
                CourseReview.course_id == course_id,
                CourseReview.user_id == user_id,
            )
            .first()
        )
        return exists is not None
    except Exception as e:
        print("❌ [has_student_reviewed] Lỗi:", e)
        traceback.print_exc()
        return False

# ======================================================
# 📊 Tính trung bình điểm của khóa học
# ======================================================
def get_course_average_rating(db: Session, course_id: str):
    """Trả về điểm trung bình (overall) của tất cả đánh giá đã duyệt."""
    try:
        result = (
            db.query(func.avg(CourseReview.overall_rating))
            .filter(
                CourseReview.course_id == course_id,
                CourseReview.status == "approved",
            )
            .scalar()
        )
        return round(result, 2) if result else 0.0
    except Exception as e:
        print("❌ [get_course_average_rating] Lỗi:", e)
        traceback.print_exc()
        return 0.0
