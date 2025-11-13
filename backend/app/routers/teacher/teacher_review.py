"""
==========================================================
🎓 ROUTER: Teacher - Reviews Management
Quản lý đánh giá khóa học mà giáo viên phụ trách
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, HTTPException, Form
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
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
    current_teacher=Depends(get_current_teacher),
    course_id: str = None,
    status: str = None,
    rating_min: float = None,
    rating_max: float = None,
    date_from: str = None,
    date_to: str = None,
):
    """
    Hiển thị danh sách & thống kê đánh giá khóa học của giáo viên.
    Có hỗ trợ bộ lọc nâng cao.
    """
    teacher = current_teacher

    # 🔹 Lấy tất cả khóa học thuộc giáo viên này
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()
    course_ids = [c.id for c in courses]

    # 🧱 Nếu giáo viên chưa có khóa học
    if not course_ids:
        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
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
                "filters": {},
                "page_title": "⭐ Đánh giá khóa học",
                "now": datetime.now(),
            },
        )

    # ======================================================
    # 🧮 Xây dựng bộ lọc linh hoạt
    # ======================================================
    query = db.query(Review).filter(Review.course_id.in_(course_ids))

    if course_id:
        query = query.filter(Review.course_id == course_id)
    if status:
        query = query.filter(Review.status == status)
    if rating_min is not None:
        query = query.filter(Review.overall_rating >= rating_min)
    if rating_max is not None:
        query = query.filter(Review.overall_rating <= rating_max)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Review.created_at >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Review.created_at <= date_to_obj)
        except ValueError:
            pass

    # 📋 Lấy kết quả
    reviews = query.order_by(Review.created_at.desc()).all()

    # ======================================================
    # 📊 Thống kê
    # ======================================================
    avg_rating = (
        db.query(func.avg(Review.overall_rating))
        .filter(Review.course_id.in_(course_ids))
        .scalar()
    ) or 0

    total_reviews = (
        db.query(func.count(Review.id))
        .filter(Review.course_id.in_(course_ids))
        .scalar()
    ) or 0

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
            and_(Review.overall_rating >= i, Review.overall_rating < i + 1),
        )
        .scalar()
        or 0
        for i in range(1, 6)
    ]

    # ======================================================
    # 📦 Render giao diện
    # ======================================================
    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "reviews/manage.html",
        {
            "request": request,
            "teacher": teacher,
            "reviews": reviews,
            "courses": courses,
            "avg_rating": round(float(avg_rating), 2),
            "total_reviews": total_reviews,
            "top_course": top_course,
            "rating_distribution": rating_distribution,
            "filters": {
                "course_id": course_id,
                "status": status,
                "rating_min": rating_min,
                "rating_max": rating_max,
                "date_from": date_from,
                "date_to": date_to,
            },
            "page_title": "⭐ Đánh giá khóa học",
            "now": datetime.now(),
        },
    )


# ======================================================
# ✅ 2️⃣ Duyệt đánh giá
# ======================================================
@router.post("/approve/{review_id}")
def approve_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    """Giáo viên duyệt đánh giá (status → approved)."""
    review = db.query(Review).get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    review.status = "approved"
    review.moderated_by = current_teacher.id
    review.moderated_at = datetime.now()
    db.commit()
    return RedirectResponse("/teacher/reviews/manage", status_code=303)


# ======================================================
# ❌ 3️⃣ Từ chối đánh giá
# ======================================================
@router.post("/reject/{review_id}")
def reject_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    """Giáo viên từ chối đánh giá (status → rejected)."""
    review = db.query(Review).get(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    review.status = "rejected"
    review.moderated_by = current_teacher.id
    review.moderated_at = datetime.now()
    db.commit()
    return RedirectResponse("/teacher/reviews/manage", status_code=303)


# ======================================================
# 🔍 4️⃣ Xem chi tiết đánh giá cụ thể
# ======================================================
@router.get("/detail/{review_id}", response_class=HTMLResponse)
def review_detail(
    review_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    """Xem chi tiết một đánh giá cụ thể."""
    review = (
        db.query(Review)
        .join(Course, Review.course_id == Course.id)
        .filter(Review.id == review_id, Course.teacher_id == current_teacher.id)
        .first()
    )
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá này.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "reviews/detail.html",
        {
            "request": request,
            "teacher": current_teacher,
            "review": review,
            "page_title": f"Chi tiết đánh giá – {review.title or 'Không có tiêu đề'}",
        },
    )
