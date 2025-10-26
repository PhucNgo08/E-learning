"""
==========================================================
🎓 ROUTER: Teacher - Reviews Management
Quản lý đánh giá khóa học mà giáo viên phụ trách
==========================================================
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

# ✅ Import nội bộ
from app.database.connection import get_db
from app.models.course import Course
from app.models.course_review import CourseReview as Review
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path


# ======================================================
# 🚀 Router
# ======================================================
router = APIRouter(
    prefix="/teacher/reviews",
    tags=["Teacher - Reviews"]
)


# ======================================================
# 🧭 0️⃣ Redirect gốc → /manage
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root():
    """Chuyển /teacher/reviews → /teacher/reviews/manage"""
    return RedirectResponse("/teacher/reviews/manage", status_code=303)


# ======================================================
# 📋 1️⃣ Trang quản lý đánh giá
# ======================================================
@router.get("/manage", response_class=HTMLResponse)
def manage_reviews(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị thống kê đánh giá khóa học của giáo viên"""
    teacher = current_teacher

    # 🔹 Lấy danh sách khóa học của giáo viên
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    course_ids = [c.id for c in courses]

    if not course_ids:
        return get_template_by_path(str(request.url.path)).TemplateResponse(
            "reviews/manage.html",
            {
                "request": request,
                "teacher": teacher,
                "reviews": [],
                "courses": [],
                "avg_rating": 0,
                "total_reviews": 0,
                "top_course": None,
                "rating_distribution": [0, 0, 0, 0, 0],
                "page_title": "⭐ Đánh giá khóa học",
                "now": datetime.now(),
            },
        )

    # 📋 Lấy danh sách đánh giá
    reviews = (
        db.query(Review)
        .filter(Review.course_id.in_(course_ids))
        .order_by(Review.created_at.desc())
        .all()
    )

    # 📊 Thống kê trung bình và tổng số
    avg_rating = (
        db.query(func.avg(Review.overall_rating))
        .filter(Review.course_id.in_(course_ids))
        .scalar()
    )
    total_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.course_id.in_(course_ids))
        .scalar()
    )

    # 🏆 Khóa học có điểm trung bình cao nhất
    top_course_row = (
        db.query(Course, func.avg(Review.overall_rating).label("avg_rating"))
        .join(Review, Review.course_id == Course.id)
        .filter(Course.teacher_id == teacher.id)
        .group_by(Course.id)
        .order_by(func.avg(Review.overall_rating).desc())
        .first()
    )
    top_course = top_course_row[0] if top_course_row else None

    # 📈 Phân bố điểm 1–5
    rating_distribution = [
        db.query(func.count(Review.id))
        .filter(
            Review.course_id.in_(course_ids),
            Review.overall_rating >= i,
            Review.overall_rating < i + 1
        )
        .scalar() or 0
        for i in range(1, 6)
    ]

    # 📦 Render giao diện
    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "reviews/manage.html",
        {
            "request": request,
            "teacher": teacher,
            "reviews": reviews,
            "courses": courses,
            "avg_rating": round(float(avg_rating or 0), 2),
            "total_reviews": total_reviews or 0,
            "top_course": top_course,
            "rating_distribution": rating_distribution,
            "page_title": "⭐ Đánh giá khóa học",
            "now": datetime.now(),
        },
    )
